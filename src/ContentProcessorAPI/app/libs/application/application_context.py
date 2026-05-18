# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Dependency-injection container and service-lifetime management.

Provides AppContext, the central DI container that the Application class
populates at startup.  Supports singleton, transient, scoped, and async
lifetime strategies, plus Azure credential/configuration wiring.
"""

import asyncio
import uuid
import weakref
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Type, TypeVar, Union

from azure.identity import DefaultAzureCredential

from .application_configuration import AppConfiguration

T = TypeVar("T")


class ServiceLifetime:
    """Constants defining how long a registered service instance lives.

    Attributes:
        SINGLETON: One instance shared across the entire application.
        TRANSIENT: A new instance created on every resolution call.
        SCOPED: One instance per scope (e.g. per HTTP request).
        ASYNC_SINGLETON: Singleton with async init/cleanup lifecycle.
        ASYNC_SCOPED: Scoped with async context-manager support.
    """

    SINGLETON = "singleton"
    TRANSIENT = "transient"  # single call
    SCOPED = "scoped"  # per request/context
    ASYNC_SINGLETON = "async_singleton"
    ASYNC_SCOPED = "async_scoped"


class ServiceDescriptor:
    """Metadata record for a single registered service.

    Responsibilities:
        1. Store the service type, implementation, and lifetime strategy.
        2. Cache the singleton/scoped instance once created.
        3. Track async cleanup requirements for async lifetimes.

    Attributes:
        service_type: The registered type or interface.
        implementation: Class, factory callable, or pre-created instance.
        lifetime: One of the ServiceLifetime constants.
        instance: Cached instance (populated for singletons after first resolution).
        is_async: Whether the service requires async resolution.
        cleanup_method: Method name called on disposal for async services.
    """

    def __init__(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[[], T], T],
        lifetime: str,
        is_async: bool = False,
        cleanup_method: str = None,
    ):
        """Initialise a service descriptor.

        Args:
            service_type: The type or interface being registered.
            implementation: Class, factory, or pre-built instance.
            lifetime: Lifetime constant from ServiceLifetime.
            is_async: True if the service needs async resolution.
            cleanup_method: Async teardown method name (default ``"close"``).
        """
        self.service_type = service_type
        self.implementation = implementation
        self.lifetime = lifetime
        self.instance = None
        self.is_async = is_async
        self.cleanup_method = cleanup_method or "close"
        self._cleanup_tasks = weakref.WeakSet()


class ServiceScope:
    """Proxy that resolves services inside an isolated scope.

    Responsibilities:
        1. Temporarily set the scope ID on the parent AppContext before resolution.
        2. Restore the previous scope after resolution to avoid cross-contamination.

    Attributes:
        _app_context: The owning AppContext container.
        _scope_id: Unique identifier for this scope.
    """

    def __init__(self, app_context: "AppContext", scope_id: str):
        """Initialise a scope (called internally by AppContext.create_scope).

        Args:
            app_context: Parent DI container.
            scope_id: Unique scope identifier.
        """
        self._app_context = app_context
        self._scope_id = scope_id

    def get_service(self, service_type: Type[T]) -> T:
        """Resolve a service within this scope's context."""
        old_scope = self._app_context._current_scope_id
        self._app_context._current_scope_id = self._scope_id
        try:
            return self._app_context.get_service(service_type)
        finally:
            self._app_context._current_scope_id = old_scope

    async def get_service_async(self, service_type: Type[T]) -> T:
        """Resolve an async service within this scope's context."""
        old_scope = self._app_context._current_scope_id
        self._app_context._current_scope_id = self._scope_id
        try:
            return await self._app_context.get_service_async(service_type)
        finally:
            self._app_context._current_scope_id = old_scope


class AppContext:
    """Central dependency-injection container with Azure credential support.

    Responsibilities:
        1. Register services under singleton, transient, scoped, or async lifetimes.
        2. Resolve services with proper caching and scope isolation.
        3. Hold the shared AppConfiguration and DefaultAzureCredential.
        4. Manage async lifecycle (init/cleanup) for async services.

    Attributes:
        configuration: Application-wide settings from Azure App Configuration.
        credential: Azure identity credential shared by all Azure SDK clients.
    """

    configuration: AppConfiguration
    credential: DefaultAzureCredential
    _services: Dict[Type, ServiceDescriptor]
    _instances: Dict[Type, Any]
    _scoped_instances: Dict[str, Dict[Type, Any]]
    _current_scope_id: str
    _async_cleanup_tasks: List[asyncio.Task]

    def __init__(self):
        """Create an empty DI container with no registered services."""
        self._services = {}
        self._instances = {}
        self._scoped_instances = {}
        self._current_scope_id = None
        self._async_cleanup_tasks = []

    def set_configuration(self, config: AppConfiguration):
        """Bind application-wide configuration settings.

        Args:
            config: Populated AppConfiguration instance.
        """
        self.configuration = config

    def set_credential(self, credential: DefaultAzureCredential):
        """Bind the Azure identity credential used by all SDK clients.

        Args:
            credential: Azure credential for service authentication.
        """
        self.credential = credential

    def add_singleton(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[[], T], T] = None,
    ) -> "AppContext":
        """Register a singleton (one shared instance) service.

        Args:
            service_type: Type or interface to register.
            implementation: Class, factory, or pre-built instance (defaults to *service_type*).

        Returns:
            Self for method chaining.
        """
        if implementation is None:
            implementation = service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=ServiceLifetime.SINGLETON,
        )
        self._services[service_type] = descriptor
        return self

    def add_transient(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[[], T]] = None,
    ) -> "AppContext":
        """Register a transient (new instance per call) service.

        Args:
            service_type: Type or interface to register.
            implementation: Class or factory (defaults to *service_type*).

        Returns:
            Self for method chaining.
        """
        if implementation is None:
            implementation = service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=ServiceLifetime.TRANSIENT,
        )
        self._services[service_type] = descriptor
        return self

    def add_scoped(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[[], T]] = None,
    ) -> "AppContext":
        """Register a scoped (one instance per scope) service.

        Args:
            service_type: Type or interface to register.
            implementation: Class or factory (defaults to *service_type*).

        Returns:
            Self for method chaining.
        """
        if implementation is None:
            implementation = service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=ServiceLifetime.SCOPED,
        )
        self._services[service_type] = descriptor
        return self

    def add_async_singleton(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[[], T]] = None,
        cleanup_method: str = "close",
    ) -> "AppContext":
        """Register an async singleton with lifecycle management.

        Args:
            service_type: Type or interface to register.
            implementation: Class or factory (defaults to *service_type*).
            cleanup_method: Method name called during shutdown.

        Returns:
            Self for method chaining.
        """
        if implementation is None:
            implementation = service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=ServiceLifetime.ASYNC_SINGLETON,
            is_async=True,
            cleanup_method=cleanup_method,
        )
        self._services[service_type] = descriptor
        return self

    def add_async_scoped(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[[], T]] = None,
        cleanup_method: str = "close",
    ) -> "AppContext":
        """Register an async scoped service with context-manager cleanup.

        Args:
            service_type: Type or interface to register.
            implementation: Class or factory (defaults to *service_type*).
            cleanup_method: Method name called when the scope exits.

        Returns:
            Self for method chaining.
        """
        if implementation is None:
            implementation = service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=ServiceLifetime.ASYNC_SCOPED,
            is_async=True,
            cleanup_method=cleanup_method,
        )
        self._services[service_type] = descriptor
        return self

    def get_service(self, service_type: Type[T]) -> T:
        """Resolve a service instance by its registered type.

        Args:
            service_type: The type or interface to look up.

        Returns:
            The resolved instance (cached for singletons/scoped).

        Raises:
            KeyError: If *service_type* was never registered.
            ValueError: If a scoped service is requested outside an active scope.
        """
        if service_type not in self._services:
            raise KeyError(f"Service {service_type.__name__} is not registered")

        descriptor = self._services[service_type]

        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if service_type in self._instances:
                return self._instances[service_type]

            instance = self._create_instance(descriptor)
            self._instances[service_type] = instance
            return instance
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            if self._current_scope_id is None:
                raise ValueError(
                    f"Scoped service {service_type.__name__} requires an active scope"
                )

            scope_services = self._scoped_instances.get(self._current_scope_id, {})
            if service_type in scope_services:
                return scope_services[service_type]

            instance = self._create_instance(descriptor)
            if self._current_scope_id not in self._scoped_instances:
                self._scoped_instances[self._current_scope_id] = {}
            self._scoped_instances[self._current_scope_id][service_type] = instance
            return instance
        else:
            return self._create_instance(descriptor)

    async def get_service_async(self, service_type: Type[T]) -> T:
        """Resolve an async service instance by its registered type.

        Args:
            service_type: The async type or interface to look up.

        Returns:
            The resolved async instance.

        Raises:
            KeyError: If *service_type* was never registered.
            ValueError: If the service is not registered as async, or if a scoped
                service is requested outside an active scope.
        """
        if service_type not in self._services:
            raise KeyError(f"Service {service_type.__name__} is not registered")

        descriptor = self._services[service_type]

        if not descriptor.is_async:
            raise ValueError(
                f"Service {service_type.__name__} is not registered as an async service"
            )

        if descriptor.lifetime == ServiceLifetime.ASYNC_SINGLETON:
            if service_type in self._instances:
                return self._instances[service_type]

            instance = await self._create_async_instance(descriptor)
            self._instances[service_type] = instance
            return instance
        elif descriptor.lifetime == ServiceLifetime.ASYNC_SCOPED:
            if self._current_scope_id is None:
                raise ValueError(
                    f"Scoped service {service_type.__name__} requires an active scope"
                )

            scope_services = self._scoped_instances.get(self._current_scope_id, {})
            if service_type in scope_services:
                return scope_services[service_type]

            instance = await self._create_async_instance(descriptor)
            if self._current_scope_id not in self._scoped_instances:
                self._scoped_instances[self._current_scope_id] = {}
            self._scoped_instances[self._current_scope_id][service_type] = instance
            return instance
        else:
            return await self._create_async_instance(descriptor)

    @asynccontextmanager
    async def create_scope(self):
        """Create an isolated scope for scoped service resolution.

        Yields:
            ServiceScope: A scope proxy for resolving scoped services.
        """
        scope_id = str(uuid.uuid4())
        old_scope = self._current_scope_id
        self._current_scope_id = scope_id

        try:
            yield ServiceScope(self, scope_id)
        finally:
            # Cleanup scoped instances
            await self._cleanup_scope(scope_id)
            self._current_scope_id = old_scope

    async def _cleanup_scope(self, scope_id: str):
        """Dispose all service instances cached under *scope_id*."""
        scope_services = self._scoped_instances.get(scope_id, {})

        for service_type, instance in scope_services.items():
            descriptor = self._services[service_type]
            if descriptor.is_async:
                if hasattr(instance, "__aexit__"):
                    await instance.__aexit__(None, None, None)
                elif hasattr(instance, descriptor.cleanup_method):
                    cleanup_method = getattr(instance, descriptor.cleanup_method)
                    if asyncio.iscoroutinefunction(cleanup_method):
                        await cleanup_method()
                    else:
                        cleanup_method()

        if scope_id in self._scoped_instances:
            del self._scoped_instances[scope_id]

    async def _create_async_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Instantiate an async service, awaiting coroutines and entering context managers."""
        implementation = descriptor.implementation

        if not callable(implementation) and not isinstance(implementation, type):
            return implementation

        if callable(implementation) and not isinstance(implementation, type):
            result = implementation()
            if asyncio.iscoroutine(result):
                instance = await result
            else:
                instance = result

            if hasattr(instance, "__aenter__"):
                await instance.__aenter__()

            return instance

        if isinstance(implementation, type):
            instance = implementation()

            if hasattr(instance, "__aenter__"):
                await instance.__aenter__()

            return instance

        raise ValueError(
            f"Unable to create async instance for {descriptor.service_type.__name__}. "
            f"Implementation type {type(implementation)} is not supported for async services."
        )

    async def shutdown_async(self):
        """Tear down the container: cancel tasks, clean up async singletons, and clear caches."""
        for task in self._async_cleanup_tasks:
            if not task.done():
                task.cancel()

        if self._async_cleanup_tasks:
            await asyncio.gather(*self._async_cleanup_tasks, return_exceptions=True)

        for service_type, instance in self._instances.items():
            descriptor = self._services[service_type]
            if descriptor.is_async and hasattr(instance, descriptor.cleanup_method):
                cleanup_method = getattr(instance, descriptor.cleanup_method)
                if asyncio.iscoroutinefunction(cleanup_method):
                    await cleanup_method()
                else:
                    cleanup_method()

        self._instances.clear()
        self._scoped_instances.clear()
        self._async_cleanup_tasks.clear()

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Synchronously create a service instance from its descriptor.

        Args:
            descriptor: Registered service metadata.

        Returns:
            The newly created or pre-existing instance.

        Raises:
            ValueError: If the implementation type is unsupported.
        """
        implementation = descriptor.implementation

        if not callable(implementation) and not isinstance(implementation, type):
            return implementation

        if callable(implementation) and not isinstance(implementation, type):
            return implementation()

        if isinstance(implementation, type):
            return implementation()

        raise ValueError(
            f"Unable to create instance for {descriptor.service_type.__name__}. "
            f"Implementation type {type(implementation)} is not supported. "
            f"Supported types: class, callable, or pre-created instance."
        )

    def is_registered(self, service_type: Type[T]) -> bool:
        """Return True if *service_type* has been registered in this container."""
        return service_type in self._services

    def get_registered_services(self) -> Dict[Type, str]:
        """Return a mapping of every registered type to its lifetime string."""
        return {
            service_type: descriptor.lifetime
            for service_type, descriptor in self._services.items()
        }
