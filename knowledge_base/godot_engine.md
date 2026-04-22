# Godot Engine Documentation Summary
Updated: 2026-04-22

## Core Concepts

### Nodes and Scenes
Everything in Godot is a Node. Nodes are the building blocks of your game.
- Nodes can be arranged in trees called Scenes
- Scenes can be instanced and reused
- Common nodes: Node2D, Node3D, Control, Sprite, CharacterBody2D/3D

### GDScript Basics
GDScript is Python-like language designed for Godot.
```gdscript
extends Node2D

@export var speed: float = 100.0

func _process(delta: float):
    position += Vector2.RIGHT * speed * delta
```

### Signals
Godot's observer pattern implementation for loose coupling.
```gdscript
signal health_changed(new_value: int)

func take_damage(amount: int):
    health -= amount
    emit_signal("health_changed", health)
```

### Autoloads (Singletons)
Global scripts accessible from anywhere in the project.
- Add via Project -> Project Settings -> Autoload
- Use for game state, managers, utilities

## Best Practices
- Use composition over inheritance
- Keep scenes small and reusable
- Use type hints for better performance
- Organize code with meaningful function names
