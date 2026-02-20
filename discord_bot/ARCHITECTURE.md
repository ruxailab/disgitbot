# Discord Bot Architecture

## Overview

This Discord bot uses a **clean, modular architecture** with **dependency injection**, **design patterns**, and **single responsibility principles**. The codebase is structured for **testability**, **maintainability**, and **scalability**.

## Architecture Patterns Applied

### 1. Dependency Injection (Service Locator Pattern)
- **Location**: `src/core/container.py`
- **Purpose**: Manages service instances and dependencies
- **Benefits**: Loose coupling, easy testing, configurable services

### 2. Strategy Pattern
- **Location**: `src/pipeline/orchestrator.py` 
- **Purpose**: Pipeline stages with interchangeable implementations
- **Benefits**: Extensible pipeline, testable stages

### 3. Template Method Pattern
- **Location**: `PipelineStage` base class
- **Purpose**: Consistent stage execution with customizable logic
- **Benefits**: Uniform error handling, logging, lifecycle management

### 4. Interface Segregation
- **Location**: `src/core/interfaces.py`
- **Purpose**: Clean contracts between components
- **Benefits**: Testable components, implementation flexibility

### 5. Factory Pattern
- **Location**: Various `create_*` functions
- **Purpose**: Consistent object creation
- **Benefits**: Centralized configuration, easy testing

## Directory Structure

```
discord_bot/src/
├── core/                    # Dependency injection & services
│   ├── container.py        # Service container (DI)
│   ├── interfaces.py       # Abstract interfaces
│   └── services.py         # Concrete implementations
├── bot/                     # Discord bot components
│   ├── bot.py              # Clean bot initialization
│   ├── commands/           # Modular command handlers
│   │   ├── user_commands.py
│   │   ├── admin_commands.py
│   │   └── analytics_commands.py
│   └── auth.py             # OAuth authentication
├── pipeline/               # Data processing pipeline
│   ├── orchestrator.py     # Pipeline orchestration
│   ├── processors/         # Modular data processors
│   │   ├── contribution_processor.py
│   │   ├── analytics_processor.py
│   │   └── metrics_processor.py
│   └── run_pipeline.py     # Unified entry point
└── utils/                  # Shared utilities
    ├── analytics/          # Chart generation
    ├── firestore.py        # Database utilities
    └── role_utils.py       # Role determination logic
```

## Design Principles Enforced

### Single Responsibility Principle
- Each class/module has **one clear purpose**
- `UserCommands` only handles user interactions
- `FirestoreService` only manages database operations
- `ContributionProcessor` only processes contribution data

### Open/Closed Principle
- **Extensible without modification**
- Add new pipeline stages without changing orchestrator
- Add new chart types without modifying existing generators
- Add new Discord commands without touching existing ones

### Dependency Inversion
- **Depend on abstractions, not concretions**
- Services depend on `IStorageService` interface
- Pipeline stages inject dependencies via constructor
- Clear interface boundaries

### Interface Segregation
- **Small, focused interfaces**
- `IStorageService` only database operations
- `IDiscordService` only Discord operations
- No fat interfaces with unused methods

## Key Components

### Service Container (`src/core/container.py`)
```python
# Register services
container.register_singleton(IStorageService, FirestoreService)
container.register_singleton(IDiscordService, DiscordBotService)

# Resolve with automatic dependency injection
storage = container.resolve(IStorageService)
```

### Pipeline Orchestrator (`src/pipeline/orchestrator.py`)
```python
# Extensible pipeline with dependency injection
orchestrator = PipelineOrchestrator()
orchestrator.add_stage(CustomStage(injected_service))
result = await orchestrator.execute_full_pipeline()
```

### Modular Commands (`src/bot/commands/`)
```python
# Clean command registration
user_commands = UserCommands(bot)
user_commands.register_commands()
```

## Benefits Achieved

###**Testability**
- **Dependency injection** enables clean testing
- **Small, focused methods** are simple to test
- **Interface-based design** allows test doubles

###**Maintainability** 
- **Single responsibility** makes changes predictable
- **Loose coupling** prevents cascading changes
- **Clear interfaces** document expected behavior

###**Scalability**
- **Add new pipeline stages** without touching existing code
- **Add new Discord commands** via new command modules
- **Add new storage backends** by implementing interfaces

###**Reusability**
- **Services can be used independently** across modules
- **Processors are composable** and reusable
- **Chart generators follow consistent patterns**

## Usage Examples

### Adding a New Pipeline Stage
```python
class CustomProcessingStage(PipelineStage):
    def __init__(self, custom_service: ICustomService):
        super().__init__("Custom Processing")
        self.service = custom_service
    
    async def _run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Custom processing logic
        return context

# Register and use
orchestrator.add_stage(CustomProcessingStage(container.resolve(ICustomService)))
```

### Adding a New Discord Command Module
```python
class MetricsCommands:
    def __init__(self, bot, storage: IStorageService):
        self.bot = bot
        self.storage = storage
    
    def register_commands(self):
        self.bot.tree.add_command(self._metrics_command())

# Register in bot initialization
metrics_commands = MetricsCommands(bot, container.resolve(IStorageService))
metrics_commands.register_commands()
```

### Adding a New Storage Backend
```python
class PostgreSQLService(IStorageService):
    def get_document(self, collection: str, document_id: str) -> Optional[Dict[str, Any]]:
        # PostgreSQL implementation
        pass

# Register new service
container.register_singleton(IStorageService, PostgreSQLService)
```

## Testing Strategy

### Unit Testing
- **Test dependencies** using interfaces
- **Test individual components** in isolation
- **Verify behavior** not implementation

### Integration Testing
- **Test service interactions** with real implementations
- **Test pipeline stages** with actual data flow
- **Test Discord commands** with bot framework

### End-to-End Testing
- **Test complete pipeline** execution
- **Test Discord bot** interactions
- **Test data persistence** and retrieval

## Configuration

### Environment Variables
```bash
DISCORD_BOT_TOKEN=your_token
GITHUB_TOKEN=your_token
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

### Service Registration
Services are automatically registered in `PipelineOrchestrator._setup_dependencies()`:
```python
container.register_singleton(IStorageService, FirestoreService)
container.register_singleton(IDiscordService, DiscordBotService)
```

## Migration Guide

### From Old Architecture
1. **Replace direct Firebase calls** with `IStorageService`
2. **Replace scattered Discord operations** with `IDiscordService`
3. **Use pipeline orchestrator** instead of individual scripts
4. **Register services** in dependency container

### Best Practices
1. **Always use interfaces** for service dependencies
2. **Inject dependencies** via constructor
3. **Keep classes focused** on single responsibility
4. **Use factory functions** for complex object creation
5. **Document interfaces** with clear contracts

This architecture ensures the codebase remains **clean**, **testable**, and **maintainable** as it grows. 