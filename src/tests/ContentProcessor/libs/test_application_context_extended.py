"""Extended tests for application_context.py to improve coverage"""
import pytest
from unittest.mock import Mock, patch
from libs.application.application_context import (
    ServiceLifetime,
    ServiceDescriptor,
    ServiceScope,
    AppContext
)


class TestServiceLifetime:
    """Test suite for ServiceLifetime constants"""
    
    def test_singleton_lifetime(self):
        """Test singleton lifetime constant"""
        assert ServiceLifetime.SINGLETON == "singleton"
    
    def test_transient_lifetime(self):
        """Test transient lifetime constant"""
        assert ServiceLifetime.TRANSIENT == "transient"
    
    def test_scoped_lifetime(self):
        """Test scoped lifetime constant"""
        assert ServiceLifetime.SCOPED == "scoped"
    
    def test_async_singleton_lifetime(self):
        """Test async singleton lifetime constant"""
        assert ServiceLifetime.ASYNC_SINGLETON == "async_singleton"
    
    def test_async_scoped_lifetime(self):
        """Test async scoped lifetime constant"""
        assert ServiceLifetime.ASYNC_SCOPED == "async_scoped"


class TestServiceDescriptor:
    """Test suite for ServiceDescriptor"""
    
    def test_service_descriptor_creation(self):
        """Test creating a service descriptor"""
        class TestService:
            pass
        
        descriptor = ServiceDescriptor(
            service_type=TestService,
            implementation=TestService,
            lifetime=ServiceLifetime.SINGLETON
        )
        
        assert descriptor.service_type == TestService
        assert descriptor.implementation == TestService
        assert descriptor.lifetime == ServiceLifetime.SINGLETON
        assert descriptor.instance is None
    
    def test_service_descriptor_with_async(self):
        """Test creating async service descriptor"""
        class AsyncService:
            async def initialize(self):
                pass
        
        descriptor = ServiceDescriptor(
            service_type=AsyncService,
            implementation=AsyncService,
            lifetime=ServiceLifetime.ASYNC_SINGLETON,
            is_async=True,
            cleanup_method="cleanup"
        )
        
        assert descriptor.is_async is True
        assert descriptor.cleanup_method == "cleanup"
    
    def test_service_descriptor_default_cleanup_method(self):
        """Test service descriptor with default cleanup method"""
        class TestService:
            pass
        
        descriptor = ServiceDescriptor(
            service_type=TestService,
            implementation=TestService,
            lifetime=ServiceLifetime.SINGLETON,
            is_async=True
        )
        
        assert descriptor.cleanup_method == "close"


class TestServiceScope:
    """Test suite for ServiceScope"""
    
    def test_service_scope_creation(self):
        """Test creating a service scope"""
        app_context = AppContext()
        scope = ServiceScope(app_context, "scope-123")
        
        assert scope._app_context == app_context
        assert scope._scope_id == "scope-123"
    
    def test_service_scope_get_service(self):
        """Test getting service from scope"""
        app_context = AppContext()
        
        class TestService:
            def __init__(self):
                self.value = "test"
        
        app_context.add_singleton(TestService, TestService)
        scope = ServiceScope(app_context, "scope-456")
        
        service = scope.get_service(TestService)
        
        assert isinstance(service, TestService)
        assert service.value == "test"


class TestAppContext:
    """Test suite for AppContext"""
    
    def test_app_context_creation(self):
        """Test creating an AppContext"""
        context = AppContext()
        
        assert context is not None
        # Configuration and credential are set via methods, not initialized to None
        assert hasattr(context, 'set_configuration')
        assert hasattr(context, 'set_credential')
    
    def test_add_singleton_with_type(self):
        """Test adding singleton service with type"""
        context = AppContext()
        
        class MyService:
            def __init__(self):
                self.name = "singleton"
        
        context.add_singleton(MyService, MyService)
        
        service1 = context.get_service(MyService)
        service2 = context.get_service(MyService)
        
        assert service1 is service2
        assert service1.name == "singleton"
    
    def test_add_singleton_with_lambda(self):
        """Test adding singleton with lambda factory"""
        context = AppContext()
        
        class MyService:
            def __init__(self, value):
                self.value = value
        
        context.add_singleton(MyService, lambda: MyService("from_lambda"))
        
        service = context.get_service(MyService)
        
        assert service.value == "from_lambda"
    
    def test_add_transient_creates_new_instances(self):
        """Test that transient services create new instances"""
        context = AppContext()
        
        class Counter:
            instance_count = 0
            
            def __init__(self):
                Counter.instance_count += 1
                self.id = Counter.instance_count
        
        context.add_transient(Counter, Counter)
        
        service1 = context.get_service(Counter)
        service2 = context.get_service(Counter)
        
        assert service1 is not service2
        assert service1.id != service2.id
    
    def test_add_scoped_service(self):
        """Test adding scoped service"""
        context = AppContext()
        
        class ScopedService:
            def __init__(self):
                self.data = "scoped"
        
        context.add_scoped(ScopedService, ScopedService)
        
        # Verify service is registered
        assert context.is_registered(ScopedService)
    
    def test_is_registered_true(self):
        """Test checking if service is registered"""
        context = AppContext()
        
        class RegisteredService:
            pass
        
        context.add_singleton(RegisteredService, RegisteredService)
        
        assert context.is_registered(RegisteredService) is True
    
    def test_is_registered_false(self):
        """Test checking if service is not registered"""
        context = AppContext()
        
        class UnregisteredService:
            pass
        
        assert context.is_registered(UnregisteredService) is False
    
    def test_get_registered_services(self):
        """Test getting list of registered services"""
        context = AppContext()
        
        class Service1:
            pass
        
        class Service2:
            pass
        
        context.add_singleton(Service1, Service1)
        context.add_transient(Service2, Service2)
        
        registered = context.get_registered_services()
        
        assert Service1 in registered
        assert Service2 in registered
    
    def test_set_configuration(self):
        """Test setting configuration"""
        context = AppContext()
        
        config = Mock()
        config.app_name = "TestApp"
        
        context.set_configuration(config)
        
        assert context.configuration == config
        assert context.configuration.app_name == "TestApp"
    
    def test_set_credential(self):
        """Test setting Azure credential"""
        context = AppContext()
        
        credential = Mock()
        credential.get_token = Mock()
        
        context.set_credential(credential)
        
        assert context.credential == credential
    
    def test_singleton_method_chaining(self):
        """Test method chaining with add_singleton"""
        context = AppContext()
        
        class Service1:
            pass
        
        class Service2:
            pass
        
        result = context.add_singleton(Service1, Service1).add_singleton(Service2, Service2)
        
        assert result == context
        assert context.is_registered(Service1)
        assert context.is_registered(Service2)
    
    def test_transient_method_chaining(self):
        """Test method chaining with add_transient"""
        context = AppContext()
        
        class Service1:
            pass
        
        class Service2:
            pass
        
        result = context.add_transient(Service1, Service1).add_transient(Service2, Service2)
        
        assert result == context
        assert context.is_registered(Service1)
        assert context.is_registered(Service2)
    
    def test_scoped_method_chaining(self):
        """Test method chaining with add_scoped"""
        context = AppContext()
        
        class Service1:
            pass
        
        class Service2:
            pass
        
        result = context.add_scoped(Service1, Service1).add_scoped(Service2, Service2)
        
        assert result == context
        assert context.is_registered(Service1)
        assert context.is_registered(Service2)
    
    def test_get_service_raises_for_unregistered(self):
        """Test that getting unregistered service raises error"""
        context = AppContext()
        
        class UnregisteredService:
            pass
        
        with pytest.raises((KeyError, ValueError, RuntimeError)):
            context.get_service(UnregisteredService)
    
    def test_complex_service_registration(self):
        """Test complex service registration scenario"""
        context = AppContext()
        
        class DatabaseService:
            def __init__(self):
                self.connected = True
        
        class LoggerService:
            def __init__(self):
                self.logs = []
        
        class BusinessService:
            def __init__(self):
                self.processed = False
        
        # Register multiple services
        context.add_singleton(DatabaseService, DatabaseService)
        context.add_transient(LoggerService, LoggerService)
        context.add_scoped(BusinessService, BusinessService)
        
        # Verify all are registered
        assert context.is_registered(DatabaseService)
        assert context.is_registered(LoggerService)
        assert context.is_registered(BusinessService)
        
        # Get services
        db = context.get_service(DatabaseService)
        logger1 = context.get_service(LoggerService)
        logger2 = context.get_service(LoggerService)
        
        assert db.connected is True
        assert logger1 is not logger2  # Transient creates new instances
    
    def test_singleton_with_instance(self):
        """Test adding singleton with pre-created instance"""
        context = AppContext()
        
        class Service:
            def __init__(self, value):
                self.value = value
        
        instance = Service("pre-created")
        context.add_singleton(Service, instance)
        
        retrieved = context.get_service(Service)
        
        assert retrieved is instance
        assert retrieved.value == "pre-created"
    
    def test_app_context_empty_state(self):
        """Test AppContext in empty state"""
        context = AppContext()
        
        registered = context.get_registered_services()
        
        # registered services might be a dict or list depending on implementation
        assert registered is not None
        if isinstance(registered, dict):
            assert len(registered) == 0
        else:
            assert len(registered) == 0
