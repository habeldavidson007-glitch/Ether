---
source: expander
generated: 2026-04-22T17:29:13.110353
category: godot_advanced
mode: coding
---

# Godot Physics & Collision Detection

## Physics Engines

### 2D Physics (Godot 4.x)
Godot uses Box2D-based 2D physics engine.

**Key Nodes:**
- `RigidBody2D` - Physics-controlled objects
- `CharacterBody2D` - Player/enemy movement
- `Area2D` - Detection zones, triggers
- `StaticBody2D` - Immovable obstacles

### 3D Physics
Uses Bullet physics engine (Godot 3.x) or custom (Godot 4.x).

**Key Nodes:**
- `RigidBody3D` - Dynamic physics objects
- `CharacterBody3D` - 3D character controller
- `Area3D` - 3D detection areas
- `StaticBody3D` - Static colliders

## Collision Layers & Masks

### Understanding the System
- **Layers**: What this object IS on (1-32)
- **Masks**: What this object CAN detect (1-32)

```gdscript
# Player setup (Layer 1, Masks 2,3)
collision_layer = 1  # Binary: 0001
collision_mask = 6   # Binary: 0110 (detects enemies & hazards)

# Enemy setup (Layer 2, Masks 1)
collision_layer = 2  # Binary: 0010
collision_mask = 1   # Binary: 0001 (detects player)
```

### Common Layer Configuration
```
Layer 1:  Player
Layer 2:  Enemies
Layer 3:  Hazards
Layer 4:  Collectibles
Layer 5:  Projectiles (player)
Layer 6:  Projectiles (enemy)
Layer 8:  Environment
Layer 9:  Triggers
```

## Collision Shapes

### Shape Types
- `RectangleShape2D` / `BoxShape3D` - Boxes
- `CircleShape2D` / `SphereShape3D` - Spheres
- `CapsuleShape2D` / `CapsuleShape3D` - Capsules
- `ConvexPolygonShape2D` / `ConvexPolygonShape3D` - Convex meshes
- `ConcavePolygonShape2D` / `ConcavePolygonShape3D` - Detailed static meshes

### Best Practices
1. Use simplest shape possible (performance)
2. Combine multiple simple shapes vs one complex shape
3. Use ConcavePolygon only for static environment
4. Adjust collision margins for stability

## Physics Materials

### Creating Bounce & Friction
```gdscript
var phys_material = PhysicsMaterial.new()
phys_material.friction = 0.3      # 0 = slippery, 1 = sticky
phys_material.bounce = 0.7        # 0 = no bounce, 1 = full bounce

$CollisionShape2D.material = phys_material
```

## Common Physics Issues

### Tunneling (Fast Objects Pass Through)
**Problem:** Fast-moving objects skip collision detection
**Solutions:**
1. Enable Continuous Collision Detection (CCD)
2. Use `_physics_process()` not `_process()`
3. Increase physics FPS (Project Settings → Physics → Common → Physics Ticks Per Second)
4. Use raycast for very fast projectiles

```gdscript
# Enable CCD for RigidBody
$RigidBody2D.constant_linear_velocity = true
$RigidBody2D.max_contacts_reported = 4
```

### Jittery Movement
**Causes:**
- Conflicting forces
- Collision shape misalignment
- Low physics FPS

**Solutions:**
1. Check for overlapping collision shapes
2. Reduce mass ratios (< 10:1)
3. Increase physics FPS to 120+
4. Use CharacterBody instead of RigidBody for players

### Rotation Locking
```gdscript
# Prevent unwanted rotation (common for platformers)
$RigidBody2D.freeze_axis_rotation = true  # Godot 4.x
# OR
$RigidBody2D.freeze = RigidBody2D.FREEZE_ROTATION  # Godot 3.x
```

## Raycasting

### 2D Raycast Example
```gdscript
func check_wall_ahead(distance: float = 50.0) -> bool:
    var space_state = get_world_2d().direct_space_state
    var from = global_position
    var to = global_position + Vector2.RIGHT * distance * facing_direction
    
    var query = PhysicsRayQueryParameters2D.create(from, to)
    query.exclude = [self]
    
    var result = space_state.intersect_ray(query)
    return result.size() > 0
```

### 3D Raycast for Shooting
```gdscript
func shoot(origin: Vector3, direction: Vector3, damage: int) -> void:
    var space_state = get_world_3d().direct_space_state
    var query = PhysicsRayQueryParameters3D.create(
        origin,
        origin + direction * 1000
    )
    
    var result = space_state.intersect_ray(query)
    if result:
        var hit_object = result.collider
        if hit_object.has_method("take_damage"):
            hit_object.take_damage(damage)
        
        # Spawn impact effect
        spawn_impact_effect(result.position, result.normal)
```

## Performance Optimization

### Physics Optimization Tips
1. **Use sleep mode** for inactive rigid bodies
2. **Layer culling** - don't check unnecessary collisions
3. **Simple shapes** over complex meshes
4. **Batch similar objects** when possible
5. **Disable collision monitoring** when not needed

```gdscript
# Disable when off-screen
func _on_visibility_changed():
    if not visible:
        collision_layer = 0
        collision_mask = 0
    else:
        collision_layer = 1
        collision_mask = 6
```

## Advanced Techniques

### Custom Force Application
```gdscript
func apply_explosion_force(position: Vector2, force: float, radius: float):
    var direction = global_position - position
    var distance = direction.length()
    
    if distance < radius:
        direction = direction.normalized()
        var falloff = 1.0 - (distance / radius)
        apply_central_impulse(direction * force * falloff)
```

### Grappling Hook Physics
```gdscript
@export var rope_length: float = 100.0
@export var swing_force: float = 500.0

func _physics_process(delta):
    if is_grappled:
        var direction = anchor_point - global_position
        var distance = direction.length()
        
        if distance > rope_length:
            direction = direction.normalized()
            var pull_force = (distance - rope_length) * 100
            apply_central_force(direction * pull_force)
        
        # Add swing momentum
        apply_central_impulse(Vector2.RIGHT * swing_force * delta)
```
