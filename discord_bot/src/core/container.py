from .singleton import Singleton
from .interfaces import (
    IRepoAnalyticsService,
    IGuildService,
    IGitHubService,
    IRoleService,
    INotificationService
)
from .services import (
    GitHubAnalyticsService,
    GuildService,
    GitHubService,
    RoleService,
    NotificationService
)

class ServiceContainer:
    def __init__(self):
        self._services = {}

    def register_singleton(self, interface, implementation):
        self._services[interface] = Singleton(implementation)
        print(f"Registered {interface.__name__} -> {implementation.__name__}")

    def resolve(self, interface):
        try:
            implementation_factory = self._services[interface]
            return implementation_factory.get_instance()
        except KeyError:
            raise Exception(f"No service registered for interface: {interface.__name__}")

def setup_dependencies() -> ServiceContainer:
    container = ServiceContainer()
    
    # container.register_singleton(IGuildService, GuildService)
    # container.register_singleton(IGitHubService, GitHubService)
    # container.register_singleton(IRoleService, RoleService)
    # container.register_singleton(INotificationService, NotificationService)
    
    container.register_singleton(IRepoAnalyticsService, GitHubAnalyticsService)
    
    print("-" * 30)
    print("Service container setup complete.")
    print("-" * 30)
    
    return container