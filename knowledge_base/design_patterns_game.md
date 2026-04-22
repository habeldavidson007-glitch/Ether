---
source: expander
generated: 2026-04-22T17:29:18.291980
category: architecture
mode: coding
---

# Game Design Patterns

## 1. Object Pool
```gdscript
class BulletPool:
    var pool: Array[Bullet] = []
    
    func get_bullet() -> Bullet:
        return pool.pop_back() if pool.size() > 0 else Bullet.new()
    
    func return_bullet(b: Bullet):
        b.reset()
        pool.append(b)
```

## 2. State Machine
```gdscript
class State:
    func enter(): pass
    func process(delta): pass
    func exit(): pass

class StateMachine:
    var current: State
    func process(delta):
        var next = current.process(delta)
        if next:
            current.exit()
            current = next
            current.enter()
```

## 3. Event Bus
```gdscript
# Global singleton
signal game_event(event_name: String, data: Dictionary)

# Publish/Subscribe
EventBus.game_event.emit("enemy_defeated", {"xp": 50})
EventBus.game_event.connect(_on_game_event)
```

## 4. Component Pattern
```gdscript
class Entity:
    var components: Dictionary = {}
    func add_component(name, comp): components[name] = comp

class HealthComponent:
    var hp: int = 100
    func take_damage(amount): hp -= amount
```
