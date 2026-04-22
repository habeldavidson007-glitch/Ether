---
source: expander
generated: 2026-04-22T17:29:13.110871
category: godot_advanced
mode: coding
---

# Godot Performance Optimization

## Rendering Optimization
- Use occlusion culling for 3D scenes
- Batch draw calls with same material
- Use texture atlases for 2D sprites
- Limit real-time lights; use baked lighting

## Physics Optimization
- Use simple collision shapes (boxes, spheres)
- Disable contact_monitor on bodies without signals
- Use layers/masks to reduce collision checks
- Freeze static bodies when not needed

## Script Optimization
- Cache node references in `_ready()`
- Use `_physics_process()` only for physics
- Avoid `get_node()` in loops
- Use `@onready` for dependent nodes

## Memory Optimization
- Use object pooling for frequent spawn/despawn
- Free resources when not needed
- Use `weakref` to prevent circular references
- Monitor memory in Debugger → Monitor → Memory
