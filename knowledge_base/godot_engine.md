---
source: godot_engine
updated: 2026-04-22T16:02:41.475000
mode: coding
---

# Godot Engine Knowledge Base

## Core Concepts

### Scene System
Godot uses a scene-based architecture where everything is a Node. Scenes can be nested to create complex hierarchies.

**Key Points:**
- Everything inherits from Node
- Scenes are reusable components
- Tree structure with parent-child relationships
- Signals for communication between nodes

### GDScript Basics
GDScript is Python-like language optimized for Godot.

```gdscript
extends Node2D

@export var speed: float = 100.0
var velocity: Vector2 = Vector2.ZERO

func _process(delta: float) -> void:
    velocity = Input.get_axis("ui_left", "ui_right") * speed
    position += velocity * delta
```

### Common Patterns

#### Singleton (Autoload)
1. Create a script
2. Go to Project → Project Settings → Autoload
3. Add your script as autoload
4. Access globally by name

#### State Machine
Use for character states (idle, walk, jump, attack).

#### Signal-Based Communication
Decouple nodes using signals instead of direct references.

### Performance Tips
- Use `_physics_process` for physics, `_process` for visuals
- Batch draw calls when possible
- Object pooling for frequently spawned objects
- Use `yield` or await for async operations

### Memory Management
- Godot handles most memory automatically
- Use `queue_free()` to remove nodes
- Be careful with circular references
- Disconnect signals when nodes are freed

## Common Issues & Solutions

### Movement Issues
**Problem:** Character moves differently on different framerates
**Solution:** Always multiply by delta in `_process` or use `_physics_process`

### Signal Connection Errors
**Problem:** "Nonexistent signal" errors
**Solution:** Check signal names, ensure emitter exists before connecting

### Export Variables Not Showing
**Problem:** @export variables don't appear in inspector
**Solution:** Save script, check variable type is exportable

## Best Practices
1. Keep scenes focused and reusable
2. Use composition over inheritance
3. Name nodes and variables clearly
4. Organize project with folders
5. Use version control
6. Test on target platforms early
