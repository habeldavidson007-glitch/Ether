---
source: expander
generated: 2026-04-22T16:28:55.560138
category: godot_advanced
mode: coding
---

# Godot Signals & Communication Patterns

## Custom Signals

### Declaration & Emission
```gdscript
# Declare signals at top of script
signal health_changed(new_value: int, old_value: int)
signal player_died
signal item_collected(item_name: String, quantity: int)

# Emit with arguments
emit_signal("health_changed", new_hp, old_hp)
# Or shorthand:
health_changed.emit(new_hp, old_hp)
```

## Connection Modes

### Disconnect Behavior
- **Default**: Auto-disconnect on object destruction
- **PERSIST**: Survives save/load (rarely needed)
- **ONE_SHOT**: Disconnects after first emission

```gdscript
# Connect with flags
enemy.health_changed.connect(_on_enemy_hit, CONNECT_ONE_SHOT)
```

## Advanced Patterns

### 1. Signal Bus (Global Event System)
```gdscript
# autoload/global_events.gd
signal game_over
signal wave_completed(wave_number: int)
signal achievement_unlocked(id: String)

# Anywhere in project
GlobalEvents.game_over.connect(_on_game_over)
GlobalEvents.emit_signal("wave_completed", 5)
```

### 2. Weak References (Prevent Memory Leaks)
```gdscript
var ref = weakref(some_node)
if ref.get_ref():
    ref.get_ref().do_something()
```

### 3. Dynamic Connections
```gdscript
# Connect all enemies to player
for enemy in get_tree().get_nodes_in_group("enemies"):
    enemy.died.connect(_on_enemy_died.bind(enemy))
```

## Debugging Signals
- Use `Object.is_connected(signal, callable)` to verify
- Check connections in Remote Inspector
- Avoid connecting in `_ready()` for frequently instanced nodes
