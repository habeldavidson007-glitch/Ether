---
source: design_patterns
updated: 2026-04-22T16:02:41.476035
mode: coding
---

# Design Patterns Knowledge Base

## Creational Patterns

### Singleton
Ensures only one instance exists.
```python
class Singleton:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**Use when:** Need single point of access (config, logger)
**Caution:** Can make testing difficult

### Factory
Creates objects without specifying exact class.
```python
class EnemyFactory:
    def create_enemy(self, enemy_type):
        if enemy_type == "goblin":
            return Goblin()
        elif enemy_type == "dragon":
            return Dragon()
```

## Structural Patterns

### Adapter
Makes incompatible interfaces work together.

### Decorator
Adds behavior dynamically without subclassing.

## Behavioral Patterns

### Observer
One-to-many dependency (publish-subscribe).

### Strategy
Encapsulates interchangeable algorithms.

## SOLID Principles

1. **Single Responsibility**: One reason to change
2. **Open/Closed**: Open for extension, closed for modification
3. **Liskov Substitution**: Subtypes must be substitutable
4. **Interface Segregation**: Many specific interfaces > one general
5. **Dependency Inversion**: Depend on abstractions, not concretions

## When to Use Patterns
- Don't force patterns prematurely
- Let needs emerge from code
- Refactor to patterns when duplication appears
