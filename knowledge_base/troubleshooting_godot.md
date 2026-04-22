---
source: expander
generated: 2026-04-22T16:28:55.560431
category: godot_advanced
mode: mixed
---

# Godot Troubleshooting Guide

## Common Issues & Solutions

### "Node not found" Error
**Cause:** Wrong path or node not yet in tree
**Fix:**
```gdscript
# Use @onready for dependent nodes
@onready var sprite = $Sprite2D

# Or check existence
if has_node("Sprite2D"):
    $Sprite2D.visible = true
```

### Memory Leak Detection
1. Open Debugger → Monitor → Memory
2. Watch for continuous growth
3. Check for circular references
4. Ensure `queue_free()` is called

### Performance Drops
1. Open Profiler (F3)
2. Check for expensive operations in `_process()`
3. Look for excessive draw calls
4. Monitor physics objects count

### Signal Not Firing
- Verify connection: `Object.is_connected()`
- Check if emitter is freed prematurely
- Ensure correct signal signature

### Build Export Issues
- Check export presets include all resources
- Verify file paths are lowercase (Linux)
- Test with debug export first
