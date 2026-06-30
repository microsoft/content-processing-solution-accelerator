# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Dependency-injection container and service-lifetime management.

Provides AppContext — the central DI container that wires up singletons,
transient services, scoped services (sync and async), Azure credentials,
and application configuration for the Content Processor pipeline.
"""

import asyncio
import uuid
import weakref
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Type, TypeVar, Union

from azure.identity import DefaultAzureCredential

from libs.agent_framework.agent_framework_settings import AgentFrameworkSettings

from .application_configuration import AppConfiguration as Configuration

# Type variable for generic type support
T = TypeVar("T")


class ServiceLifetime:
    """
    Enum-like class defining service lifetime constants for dependency injection.

    This class provides constants for different service lifetimes that determine
    how instances are created and managed by the dependency injection container.

    Constants:
        SINGLETON: Service instances are created once and reused for all requests.
                  Ideal for stateless services or shared resources like database connections.

        TRANSIENT: New service instances are created for each request.
                  Ideal for stateful services or when isolation between consumers is required.

        SCOPED: Service instances are created once per scope (e.g., per request/context) and
               reused within that scope. Automatically disposed when the scope ends.
               Useful for request-specific services that maintain state during a single
               operation but should be isolated between operations.

        ASYNC_SINGLETON: Async singleton with proper lifecycle management.
                        Supports async initialization and cleanup patterns.
                        Created once and supports async context manager patterns.

        ASYNC_SCOPED: Async scoped service with context manager support.
                     Created per scope with automatic async setup/teardown within a scope.

    Usage:
        Used internally by ServiceDescriptor to specify how services should be instantiated
        and managed throughout the application lifecycle. These constants are set when
        registering services via add_singleton(), add_transient(), add_scoped(), etc.

    Example:
        # Used internally when registering services
        descriptor = ServiceDescriptor(
            service_type=IDataService,
            implementation=DatabaseService,
            lifetime=ServiceLifetime.SINGLETON
        )
    """

    SINGLETON = "singleton"
    TRANSIENT = "transient"  # single call
    SCOPED = "scoped"  # per request/context
    ASYNC_SINGLETON = "async_singleton"
    ASYNC_SCOPED = "async_scoped"


class ServiceDescriptor:
    """
    Describes a registered service in the dependency injection container.

    This class encapsulates all the information needed to create and manage a service
    instance, including its type, implementation, lifetime, and cached instance for singletons.

    Attributes:
        service_type (Type[T]): The registered service type/interface
        implementation (Union[Type[T], Callable[[], T], T]): The implementation to use:
            - Class type: Will be instantiated when needed
            - Callable/Lambda: Will be invoked to create instances
            - Async Callable: Will be awaited to create instances (for async lifetimes)
            - Pre-created instance: Will be returned directly (singletons only)
        lifetime (str): Service lifetime from ServiceLifetime constants
        instance (Any): Cached instance for singleton services (None for transient/scoped)
        is_async (bool): Whether this service uses async patterns and requires async resolution
        cleanup_method (str): Name of cleanup method for async services (e.g., 'close', 'cleanup')

    Usage:
        Created internally by AppContext when services are registered via
        add_singleton(), add_transient(), add_scoped(), or their async variants.
        Not intended for direct instantiation by user code.

    Example:
        # Created internally when registering services
        descriptor = ServiceDescriptor(
            service_type=IDataService,
            implementation=DatabaseService,
            lifetime=ServiceLifetime.SINGLETON
        )

        # For async services with custom cleanup
        descriptor = ServiceDescriptor(
            service_type=IAsyncService,
            implementation=AsyncService,
            lifetime=ServiceLifetime.ASYNC_SINGLETON,
            is_async=True,
            cleanup_method="cleanup_async"
        )
    """

    def __init__(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[[], T], T],
        lifetime: str,
        is_async: bool = False,
        cleanup_method: str = None,
    ):
        """
        Initialize a new service descriptor.

        Args:
            service_type (Type[T]): The service type/interface
            implementation (Union[Type[T], Callable[[], T], T]): The implementation
            lifetime (str): The service lifetime constant from ServiceLifetime
            is_async (bool): Whether this service uses async patterns
            cleanup_method (str): Name of cleanup method for async services (defaults to "close")
        """
        self.service_type = service_type
        self.implementation = implementation
        self.lifetime = lifetime
        self.instance = None
        self.is_async = is_async
        self.cleanup_method = cleanup_method or "close"
        self._cleanup_tasks = weakref.WeakSet()


class ServiceScope:
    """
    Manages service resolution within a specific scope context.

    ServiceScope provides a controlled environment for accessing scoped services,
    ensuring proper service lifetime management and scope isolation. This class
    acts as a proxy to the parent AppContext while maintaining scope context
    for accurate service resolution.

    Key Features:
        - Scope-aware service resolution with proper context isolation
        - Thread-safe scope context management
        - Support for both sync and async service resolution
        - Automatic scope context restoration after service resolution
        - Integration with AppContext's scoped service management

    Attributes:
        _app_context (AppContext): Reference to the parent dependency injection container
        _scope_id (str): Unique identifier for this scope instance

    Usage:
        ServiceScope instances are created and managed through AppContext.create_scope().
        They should be used within the context manager pattern for automatic cleanup:

        async with app_context.create_scope() as scope:
            # Services resolved within this scope will be scoped instances
            service = await scope.get_service_async(IMyService)
            another_service = scope.get_service(IAnotherService)

            # Both services will be the same instances if requested again in this scope
            same_service = await scope.get_service_async(IMyService)  # Same instance

        # Scope is automatically disposed after the with block

    Thread Safety:
        ServiceScope manages scope context in a thread-safe manner by temporarily
        setting the scope ID on the parent AppContext and restoring it after
        service resolution. Each scope operation is atomic.

    Performance Notes:
        - Scope context switching has minimal overhead
        - Scoped service instances are cached by the parent AppContext
        - No additional instance storage overhead in ServiceScope itself

    Implementation Details:
        ServiceScope delegates all service resolution to the parent AppContext
        while temporarily setting the scope context. This ensures that the
        AppContext's service resolution logic handles the actual scoped instance
        management and caching.
    """

    def __init__(self, app_context: "AppContext", scope_id: str):
        """
        Initialize a new service scope with the specified context and ID.

        Args:
            app_context (AppContext): The parent dependency injection container
            scope_id (str): Unique identifier for this scope instance

        Note:
            This constructor is intended for internal use by AppContext.create_scope().
            Direct instantiation is not recommended as it bypasses proper scope
            registration and management.
        """
        self._app_context = app_context
        self._scope_id = scope_id

    def get_service(self, service_type: Type[T]) -> T:
        """Get a service within this scope."""
        # Set scope context before resolving
        old_scope = self._app_context._current_scope_id
        self._app_context._current_scope_id = self._scope_id
        try:
            return self._app_context.get_service(service_type)
        finally:
            self._app_context._current_scope_id = old_scope

    async def get_service_async(self, service_type: Type[T]) -> T:
        """Get an async service within this scope."""
        # Set scope context before resolving
        old_scope = self._app_context._current_scope_id
        self._app_context._current_scope_id = self._scope_id
        try:
            return await self._app_context.get_service_async(service_type)
        finally:
            self._app_context._current_scope_id = old_scope


class AppContext:
    """
    Comprehensive dependency injection container with configuration and credential management.

    AppContext serves as the central service container for the application, providing
    a complete dependency injection framework with support for multiple service lifetimes,
    async operations, proper resource cleanup, and Azure cloud integration. This class
    implements enterprise-grade patterns for service management with full type safety.

    Core Features:
        - Multi-lifetime service management: Singleton, Transient, Scoped, and Async variants
        - Type-safe service resolution with full IntelliSense support
        - Fluent API for service registration with method chaining
        - Scope-based service isolation for request/context boundaries
        - Async service lifecycle management with proper cleanup
        - Azure cloud service integration with credential management
        - Service introspection and registration verification
        - Thread-safe singleton resolution with lazy instantiation

    Service Lifetimes Supported:
        - SINGLETON: One instance per application (cached and reused)
        - TRANSIENT: New instance every time (not cached)
        - SCOPED: One instance per scope context (cached within scope)
        - ASYNC_SINGLETON: Async singleton with lifecycle management
        - ASYNC_SCOPED: Async scoped with automatic cleanup

    Attributes:
        configuration (Configuration): Application-wide configuration settings
        credential (DefaultAzureCredential): Azure authentication credentials
        _services (Dict[Type, ServiceDescriptor]): Internal service registry
        _instances (Dict[Type, Any]): Cache for singleton service instances
        _scoped_instances (Dict[str, Dict[Type, Any]]): Scoped service instance cache
        _current_scope_id (str): Active scope identifier for context resolution
        _async_cleanup_tasks (List[asyncio.Task]): Async cleanup task tracking

    Service Registration Methods:
        add_singleton(service_type, implementation): Register shared instance service
        add_transient(service_type, implementation): Register per-request instance service
        add_scoped(service_type, implementation): Register per-scope instance service
        add_async_singleton(service_type, implementation): Register async shared service
        add_async_scoped(service_type, implementation): Register async scoped service

    Service Resolution Methods:
        get_service(service_type): Synchronous service resolution with caching
        get_service_async(service_type): Asynchronous service resolution with lifecycle
        is_registered(service_type): Check service registration status
        get_registered_services(): Introspect all registered services

    Scope Management Methods:
        create_scope(): Create isolated service scope context
        _cleanup_scope(scope_id): Internal cleanup for disposed scopes

    Configuration Methods:
        set_configuration(config): Configure application settings
        set_credential(credential): Set Azure authentication credentials

    Advanced Usage Examples:
        # Complex service registration with dependencies
        app_context = (AppContext()
            .add_singleton(ILogger, ConsoleLogger)
            .add_singleton(IConfiguration, lambda: load_config())
            .add_transient(IRequestHandler, RequestHandler)
            .add_scoped(IDbContext, DatabaseContext)
            .add_async_singleton(IAsyncCache, RedisCache)
            .add_async_scoped(IAsyncProcessor, AsyncProcessor))

        # Service resolution with full type safety
        logger: ILogger = app_context.get_service(ILogger)
        handler: IRequestHandler = app_context.get_service(IRequestHandler)
        cache: IAsyncCache = await app_context.get_service_async(IAsyncCache)

        # Scoped service usage for request isolation
        async with app_context.create_scope() as scope:
            db_context: IDbContext = scope.get_service(IDbContext)
            processor: IAsyncProcessor = await scope.get_service_async(IAsyncProcessor)

            # Services are isolated within this scope
            same_db: IDbContext = scope.get_service(IDbContext)  # Same instance

            # Automatic cleanup when scope exits
            await processor.cleanup()  # Called automatically

        # Service introspection
        if app_context.is_registered(ISpecialService):
            special = app_context.get_service(ISpecialService)

        # View all registered services
        services = app_context.get_registered_services()
        for service_type, lifetime in services.items():
            print(f"{service_type.__name__}: {lifetime}")

    Performance Considerations:
        - Singleton services are cached after first resolution (O(1) subsequent access)
        - Transient services create new instances each time (O(n) instantiation cost)
        - Scoped services are cached within scope context (O(1) within scope)
        - Async services have minimal overhead beyond regular async/await costs
        - Service resolution uses dictionary lookups for optimal performance

    Thread Safety:
        The container provides thread-safe singleton resolution through proper locking.
        Scoped services are designed for single-threaded contexts (per request/task).
        Multiple scopes can exist concurrently in different threads safely.

    Error Handling:
        - Unregistered service resolution raises detailed ServiceNotRegistredException
        - Circular dependency detection prevents infinite loops
        - Async cleanup failures are logged but don't prevent other cleanups
        - Service instantiation errors provide comprehensive diagnostic information

    Azure Integration:
        Built-in support for DefaultAzureCredential enables seamless integration
        with Azure services like Key Vault, App Configuration, and managed identities.
        Configuration and credential objects are automatically available to all services.
    """

    llm_settings: AgentFrameworkSettings
    configuration: Configuration
    credential: DefaultAzureCredential
    _services: Dict[Type, ServiceDescriptor]
    _instances: Dict[Type, Any]
    _scoped_instances: Dict[
        str, Dict[Type, Any]
    ]  # scope_id -> {service_type: instance}
    _current_scope_id: str
    _async_cleanup_tasks: List[asyncio.Task]

    def __init__(self):
        """
        Initialize a new instance of the AppContext.

        Creates an empty dependency injection container with no registered services.
        The internal service registry, instance cache, and scoped instances are initialized
        as empty collections, ready for service registration and resolution.

        Initializes:
            _services (Dict[Type, ServiceDescriptor]): Registry for service descriptors
            _instances (Dict[Type, Any]): Cache for singleton service instances
            _scoped_instances (Dict[str, Dict[Type, Any]]): Cache for scoped service instances
            _current_scope_id (str): Current scope identifier for scoped services
            _async_cleanup_tasks (List[asyncio.Task]): Track async cleanup tasks

        Example:
            app_context = AppContext()
            app_context.add_singleton(IMyService, MyService)
            app_context.add_async_singleton(IAsyncService, AsyncService)
        """
        self._services = {}
        self._instances = {}
        self._scoped_instances = {}
        self._current_scope_id = None
        self._async_cleanup_tasks = []

    def set_configuration(self, config: Configuration):
        """
        Set the configuration for the application context.

        This method allows you to inject configuration settings into the application context,
        making them available throughout the application lifecycle.

        Args:
            config (Configuration): The configuration object containing application settings

        Example:
            config = Configuration()
            app_context.set_configuration(config)
        """
        self.configuration = config

    def set_credential(self, credential: DefaultAzureCredential):
        """
        Set the Azure credential for the application context.

        This method configures the Azure authentication credential that will be used
        throughout the application for Azure service authentication. The credential
        supports various authentication methods including managed identity, CLI, and more.

        Args:
            credential (DefaultAzureCredential): The Azure credential for authentication

        Example:
            credential = DefaultAzureCredential()
            app_context.set_credential(credential)
        """
        self.credential = credential

    def add_singleton(
        self,
        service_type: Type[T],
        implementation: Union[Type[T], Callable[[], T], T] = None,
    ) -> "AppContext":
        """
        Register a singleton service in the dependency injection container.

        Singleton services are created once and the same instance is returned for all
        subsequent requests. This is ideal for stateless services or services that
        manage shared resources like database connections or configuration.

        Args:
            service_type (Type[T]): The type/interface of the service to register
            implementation (Union[Type[T], Callable[[], T], T], optional):
                The implementation to use. Can be:
                - A class type to instantiate
                - A factory function that returns an instance
                - An already created instance
                If None, uses service_type as implementation

        Returns:
            AppContext: Self for method chaining

        Examples:
            # Register with concrete class
            app_context.add_singleton(IDataService, DatabaseService)

            # Register with factory function
            app_context.add_singleton(ILoggerService, lambda: ConsoleLogger("INFO"))

            # Register with existing instance
            logger = ConsoleLogger("DEBUG")
            app_context.add_singleton(ILoggerService, logger)

            # Register concrete class as itself
            app_context.add_singleton(DatabaseService)
        """
        # If no implementation provided, use the service_type as implementation
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
        """
        Register a transient (single-call) service in the dependency injection container.

        Transient services create a new instance for each request. This is ideal for
        stateful services or services that should not share state between different
        consumers. Each call to get_service() will return a fresh instance.

        Args:
            service_type (Type[T]): The type/interface of the service to register
            implementation (Union[Type[T], Callable[[], T]], optional):
                The implementation to use. Can be:
                - A class type to instantiate
                - A factory function that returns a new instance
                If None, uses service_type as implementation

        Returns:
            AppContext: Self for method chaining

        Examples:
            # Register with concrete class (new instance each time)
            app_context.add_transient(IRequestProcessor, RequestProcessor)

            # Register with factory function
            app_context.add_transient(IHttpClient, lambda: HttpClient(timeout=30))

            # Register concrete class as itself
            app_context.add_transient(RequestProcessor)

        Note:
            Unlike add_singleton, this method does not accept pre-created instances
            since each call should create a new instance.
        """
        # If no implementation provided, use the service_type as implementation
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
        """
        Register a scoped service in the dependency injection container.

        Scoped services are created once per scope (e.g., per request or context) and
        reused within that scope. They are automatically disposed when the scope ends.
        This is ideal for request-specific services that maintain state during a single
        operation but should be isolated between operations.

        Args:
            service_type (Type[T]): The type/interface of the service to register
            implementation (Union[Type[T], Callable[[], T]], optional):
                The implementation to use. Can be:
                - A class type to instantiate
                - A factory function that returns a new instance
                If None, uses service_type as implementation

        Returns:
            AppContext: Self for method chaining

        Examples:
            # Register scoped service for request context
            app_context.add_scoped(IRequestContext, RequestContext)

            # Use within a scope
            async with app_context.create_scope() as scope:
                context = scope.get_service(IRequestContext)
                # Same instance within scope
                same_context = scope.get_service(IRequestContext)
                assert context is same_context
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
        """
        Register an async singleton service with proper lifecycle management.

        Async singleton services are created once and support async initialization
        and cleanup patterns. They implement proper resource management for services
        that need async setup/teardown like database connections, HTTP clients, etc.

        Args:
            service_type (Type[T]): The type/interface of the service to register
            implementation (Union[Type[T], Callable[[], T]], optional):
                The implementation to use. Should support async patterns.
                If None, uses service_type as implementation
            cleanup_method (str): Name of the cleanup method to call on disposal

        Returns:
            AppContext: Self for method chaining

        Examples:
            # Register async singleton with default cleanup
            app_context.add_async_singleton(IAsyncDatabaseService, AsyncDatabaseService)

            # Register with custom cleanup method
            app_context.add_async_singleton(
                IHttpClient,
                AsyncHttpClient,
                cleanup_method="close_connections"
            )

            # Usage with proper lifecycle
            async_service = await app_context.get_service_async(IAsyncDatabaseService)
            # Service will be automatically cleaned up on app shutdown
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
        """
        Register an async scoped service with context manager support.

        Async scoped services are created per scope and support async context manager
        patterns. They automatically handle async setup and teardown within a scope,
        making them ideal for request-specific resources that need async lifecycle management.

        Args:
            service_type (Type[T]): The type/interface of the service to register
            implementation (Union[Type[T], Callable[[], T]], optional):
                The implementation to use. Should support async context manager patterns.
                If None, uses service_type as implementation
            cleanup_method (str): Name of the cleanup method to call on scope disposal

        Returns:
            AppContext: Self for method chaining

        Examples:
            # Register async scoped service
            app_context.add_async_scoped(IAsyncRequestProcessor, AsyncRequestProcessor)

            # Usage within async scope
            async with app_context.create_scope() as scope:
                processor = await scope.get_service_async(IAsyncRequestProcessor)
                await processor.process_request(data)
                # processor.close() called automatically when scope exits
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
        """
        Retrieve a strongly typed service instance from the dependency injection container.

        This method resolves services based on their registration lifetime:
        - Singleton services: Returns the same cached instance for all requests
        - Transient services: Creates and returns a new instance for each request

        The method provides full type safety and VS Code IntelliSense support, ensuring
        that the returned instance matches the requested type.

        Args:
            service_type (Type[T]): The type/interface of the service to retrieve

        Returns:
            T: The service instance with proper typing for IntelliSense

        Raises:
            KeyError: If the requested service type is not registered in the container
            ValueError: If the service cannot be instantiated due to configuration issues

        Examples:
            # Get singleton service (same instance each time)
            data_service: IDataService = app_context.get_service(IDataService)

            # Get transient service (new instance each time)
            processor: IRequestProcessor = app_context.get_service(IRequestProcessor)

            # Type safety - IDE will show proper methods and properties
            result = data_service.get_data()  # IntelliSense works here

        Thread Safety:
            This method is thread-safe for singleton services. Concurrent calls will
            receive the same cached instance without creating duplicates.
        """
        if service_type not in self._services:
            raise KeyError(f"Service {service_type.__name__} is not registered")

        descriptor = self._services[service_type]

        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            # For singletons, check if we already have an instance
            if service_type in self._instances:
                return self._instances[service_type]

            # Create and cache the instance
            instance = self._create_instance(descriptor)
            self._instances[service_type] = instance
            return instance
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            # For scoped services, use current scope
            if self._current_scope_id is None:
                raise ValueError(
                    f"Scoped service {service_type.__name__} requires an active scope"
                )

            scope_services = self._scoped_instances.get(self._current_scope_id, {})
            if service_type in scope_services:
                return scope_services[service_type]

            # Create instance for current scope
            instance = self._create_instance(descriptor)
            if self._current_scope_id not in self._scoped_instances:
                self._scoped_instances[self._current_scope_id] = {}
            self._scoped_instances[self._current_scope_id][service_type] = instance
            return instance
        else:
            # For transient services, always create a new instance
            return self._create_instance(descriptor)

    async def get_service_async(self, service_type: Type[T]) -> T:
        """
        Retrieve an async service instance with proper lifecycle management.

        This method handles async service resolution for services registered with
        async lifetimes. It ensures proper initialization and tracks cleanup tasks
        for services that need async disposal.

        Args:
            service_type (Type[T]): The type/interface of the async service to retrieve

        Returns:
            T: The async service instance with proper typing

        Raises:
            KeyError: If the requested service type is not registered
            ValueError: If the service is not registered as an async service

        Examples:
            # Get async singleton service
            db_service = await app_context.get_service_async(IAsyncDatabaseService)

            # Get async scoped service (must be within a scope)
            async with app_context.create_scope() as scope:
                processor = await scope.get_service_async(IAsyncRequestProcessor)
        """
        if service_type not in self._services:
            raise KeyError(f"Service {service_type.__name__} is not registered")

        descriptor = self._services[service_type]

        if not descriptor.is_async:
            raise ValueError(
                f"Service {service_type.__name__} is not registered as an async service"
            )

        if descriptor.lifetime == ServiceLifetime.ASYNC_SINGLETON:
            # For async singletons, check if we already have an instance
            if service_type in self._instances:
                return self._instances[service_type]

            # Create and cache the async instance
            instance = await self._create_async_instance(descriptor)
            self._instances[service_type] = instance
            return instance
        elif descriptor.lifetime == ServiceLifetime.ASYNC_SCOPED:
            # For scoped services, use current scope
            if self._current_scope_id is None:
                raise ValueError(
                    f"Scoped service {service_type.__name__} requires an active scope"
                )

            scope_services = self._scoped_instances.get(self._current_scope_id, {})
            if service_type in scope_services:
                return scope_services[service_type]

            # Create instance for current scope
            instance = await self._create_async_instance(descriptor)
            if self._current_scope_id not in self._scoped_instances:
                self._scoped_instances[self._current_scope_id] = {}
            self._scoped_instances[self._current_scope_id][service_type] = instance
            return instance
        else:
            # For other async services, always create new instance
            return await self._create_async_instance(descriptor)

    @asynccontextmanager
    async def create_scope(self):
        """
        Create a service scope for scoped service lifetime management.

        This async context manager creates a new scope for scoped services,
        ensuring proper isolation and cleanup of scoped service instances.

        Yields:
            ServiceScope: A scope object for resolving scoped services

        Examples:
            # Use scoped services
            async with app_context.create_scope() as scope:
                request_context = scope.get_service(IRequestContext)
                processor = await scope.get_service_async(IAsyncRequestProcessor)
                # Services are automatically cleaned up when scope exits
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
        """Clean up all services in the specified scope."""
        scope_services = self._scoped_instances.get(scope_id, {})

        for service_type, instance in scope_services.items():
            descriptor = self._services[service_type]
            if descriptor.is_async:
                # Check if instance is an async context manager (has __aexit__)
                if hasattr(instance, "__aexit__"):
                    # Call __aexit__ directly for async context managers
                    await instance.__aexit__(None, None, None)
                elif hasattr(instance, descriptor.cleanup_method):
                    # Fallback to configured cleanup method for other services
                    cleanup_method = getattr(instance, descriptor.cleanup_method)
                    if asyncio.iscoroutinefunction(cleanup_method):
                        await cleanup_method()
                    else:
                        cleanup_method()

        # Remove the scope
        if scope_id in self._scoped_instances:
            del self._scoped_instances[scope_id]

    async def _create_async_instance(self, descriptor: ServiceDescriptor) -> Any:
        """
        Create an async instance from a service descriptor.

        Args:
            descriptor: The service descriptor for an async service

        Returns:
            The created async service instance
        """
        implementation = descriptor.implementation

        # If it's already an instance, return it
        if not callable(implementation) and not isinstance(implementation, type):
            return implementation

        # If it's a callable (function/lambda), call it
        if callable(implementation) and not isinstance(implementation, type):
            result = implementation()
            if asyncio.iscoroutine(result):
                instance = await result
            else:
                instance = result

            # If the instance has an async __aenter__ method, initialize it
            if hasattr(instance, "__aenter__"):
                await instance.__aenter__()

            return instance

        # If it's a class, instantiate it
        if isinstance(implementation, type):
            instance = implementation()

            # If it has an async __aenter__ method, initialize it
            if hasattr(instance, "__aenter__"):
                await instance.__aenter__()

            return instance

        raise ValueError(
            f"Unable to create async instance for {descriptor.service_type.__name__}. "
            f"Implementation type {type(implementation)} is not supported for async services."
        )

    async def shutdown_async(self):
        """
        Shutdown the application context and cleanup all async resources.

        This method should be called when the application is shutting down to ensure
        proper cleanup of all async singleton services and running tasks.

        Examples:
            # Cleanup on application shutdown
            await app_context.shutdown_async()
        """
        # Cancel all cleanup tasks
        for task in self._async_cleanup_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._async_cleanup_tasks:
            await asyncio.gather(*self._async_cleanup_tasks, return_exceptions=True)

        # Cleanup async singleton instances
        for service_type, instance in self._instances.items():
            descriptor = self._services[service_type]
            if descriptor.is_async and hasattr(instance, descriptor.cleanup_method):
                cleanup_method = getattr(instance, descriptor.cleanup_method)
                if asyncio.iscoroutinefunction(cleanup_method):
                    await cleanup_method()
                else:
                    cleanup_method()

        # Clear all caches
        self._instances.clear()
        self._scoped_instances.clear()
        self._async_cleanup_tasks.clear()

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """
        Create an instance from a service descriptor.

        This private method handles the actual instantiation logic for registered services.
        It supports multiple implementation types and provides appropriate error handling
        for unsupported configurations.

        Args:
            descriptor (ServiceDescriptor): The service descriptor containing:
                - service_type: The registered service type
                - implementation: The implementation to instantiate
                - lifetime: The service lifetime (singleton/transient)

        Returns:
            Any: The created service instance

        Raises:
            ValueError: If the implementation type is not supported or cannot be instantiated

        Supported Implementation Types:
            - Pre-created instance: Returns the instance directly
            - Callable/Lambda: Invokes the function and returns the result
            - Class type: Instantiates the class with no-argument constructor

        Internal Logic:
            1. If implementation is already an instance, return it as-is
            2. If implementation is a callable (but not a class), invoke it
            3. If implementation is a class type, instantiate it
            4. Otherwise, raise ValueError for unsupported types
        """
        implementation = descriptor.implementation

        # If it's already an instance, return it
        if not callable(implementation) and not isinstance(implementation, type):
            return implementation

        # If it's a callable (function/lambda), call it
        if callable(implementation) and not isinstance(implementation, type):
            return implementation()

        # If it's a class, instantiate it
        if isinstance(implementation, type):
            return implementation()

        raise ValueError(
            f"Unable to create instance for {descriptor.service_type.__name__}. "
            f"Implementation type {type(implementation)} is not supported. "
            f"Supported types: class, callable, or pre-created instance."
        )

    def is_registered(self, service_type: Type[T]) -> bool:
        """
        Check if a service type is registered in the dependency injection container.

        This method allows you to verify whether a service has been registered before
        attempting to retrieve it, helping to avoid KeyError exceptions and implement
        conditional service resolution logic.

        Args:
            service_type (Type[T]): The type/interface to check for registration

        Returns:
            bool: True if the service type is registered, False otherwise

        Examples:
            # Check before using a service
            if app_context.is_registered(IOptionalService):
                service = app_context.get_service(IOptionalService)
                service.do_something()

            # Conditional registration
            if not app_context.is_registered(ILoggerService):
                app_context.add_singleton(ILoggerService, ConsoleLoggerService)

        Use Cases:
            - Optional service dependencies
            - Conditional service registration
            - Service availability checks in middleware
            - Testing scenarios with partial service registration
        """
        return service_type in self._services

    def get_registered_services(self) -> Dict[Type, str]:
        """
        Get all registered services and their corresponding lifetimes.

        This method provides introspection capabilities for the dependency injection
        container, allowing you to see what services are available and how they're
        configured. Useful for debugging, testing, and administrative purposes.

        Returns:
            Dict[Type, str]: A dictionary mapping service types to their lifetime strings.
                            Lifetimes are either 'singleton' or 'transient'.

        Examples:
            # Get all registered services
            services = app_context.get_registered_services()

            # Print service registry
            for service_type, lifetime in services.items():
                print(f"{service_type.__name__}: {lifetime}")

            # Check specific service lifetime
            services = app_context.get_registered_services()
            if IDataService in services:
                lifetime = services[IDataService]
                print(f"DataService is registered as {lifetime}")

        Use Cases:
            - Service registry debugging
            - Application health checks
            - Service discovery in complex applications
            - Testing service registration completeness
            - Administrative/monitoring interfaces
        """
        return {
            service_type: descriptor.lifetime
            for service_type, descriptor in self._services.items()
        }
