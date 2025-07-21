"""
Service Container

Dependency injection container for managing service instances and dependencies.
"""

from typing import Dict, Any, TypeVar, Type, Optional, Callable

T = TypeVar('T')

class ServiceContainer:
    """
    Dependency injection container implementing Service Locator pattern.
    Manages service registration, instantiation, and lifecycle.
    """
    
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._singletons: Dict[Type, Any] = {}
        self._is_singleton: Dict[Type, bool] = {}
    
    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> 'ServiceContainer':
        """Register a service as singleton (one instance for the application)."""
        self._services[interface] = implementation
        self._is_singleton[interface] = True
        return self
    
    def register_transient(self, interface: Type[T], implementation: Type[T]) -> 'ServiceContainer':
        """Register a service as transient (new instance every time)."""
        self._services[interface] = implementation
        self._is_singleton[interface] = False
        return self
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> 'ServiceContainer':
        """Register a factory function for creating service instances."""
        self._factories[interface] = factory
        self._is_singleton[interface] = False
        return self
    
    def register_instance(self, interface: Type[T], instance: T) -> 'ServiceContainer':
        """Register a pre-created instance."""
        self._singletons[interface] = instance
        self._is_singleton[interface] = True
        return self
    
    def resolve(self, interface: Type[T]) -> T:
        """Resolve a service instance by interface type."""
        # Check for pre-registered instance
        if interface in self._singletons:
            return self._singletons[interface]
        
        # Check for factory
        if interface in self._factories:
            instance = self._factories[interface]()
            if self._is_singleton.get(interface, False):
                self._singletons[interface] = instance
            return instance
        
        # Check for registered service
        if interface in self._services:
            implementation = self._services[interface]
            
            # Create instance
            if hasattr(implementation, '__init__'):
                # Try to inject dependencies
                instance = self._create_with_dependencies(implementation)
            else:
                instance = implementation()
            
            # Store singleton if needed
            if self._is_singleton.get(interface, False):
                self._singletons[interface] = instance
            
            return instance
        
        raise ValueError(f"Service {interface.__name__} not registered")
    
    def _create_with_dependencies(self, implementation: Type[T]) -> T:
        """Create instance with automatic dependency injection."""
        import inspect
        
        # Get constructor parameters
        sig = inspect.signature(implementation.__init__)
        params = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # Try to resolve parameter type
            if param.annotation != inspect.Parameter.empty:
                try:
                    params[param_name] = self.resolve(param.annotation)
                except ValueError:
                    # Skip if can't resolve - let implementation handle it
                    pass
        
        return implementation(**params)
    
    def is_registered(self, interface: Type[T]) -> bool:
        """Check if a service is registered."""
        return (interface in self._services or 
                interface in self._factories or 
                interface in self._singletons)
    
    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        self._is_singleton.clear()

# Global container instance
container = ServiceContainer() 