"""
Ether Knowledge Expander - Generate Specialized Knowledge Files
================================================================
Purpose: Automatically generate comprehensive, specialized knowledge files
to expand the knowledge base from 7 files to 50+ files.

Features:
- Generates deep-dive technical content for Godot, C++, and programming
- Creates troubleshooting guides
- Produces architecture pattern documentation
- Adds performance optimization guides
- Generates API reference summaries

Usage:
    # Generate all expanded knowledge files
    python courier/expander.py
    
    # Generate specific category
    python courier/expander.py --category godot_advanced
    
    # List available categories
    python courier/expander.py --list
"""

import argparse
import os
from pathlib import Path
from typing import Dict, List, Callable
from datetime import datetime


class KnowledgeGenerator:
    """Base class for knowledge generators."""
    
    def __init__(self, name: str, category: str, mode: str = "coding"):
        self.name = name
        self.category = category
        self.mode = mode
    
    def generate(self) -> str:
        """Generate knowledge content. Override in subclasses."""
        raise NotImplementedError
    
    def get_filename(self) -> str:
        """Get output filename."""
        return f"{self.name}.md"


# ============================================================================
# GODOT ADVANCED GENERATORS
# ============================================================================

class GodotPhysicsGenerator(KnowledgeGenerator):
    """Godot physics and collision detection."""
    
    def __init__(self):
        super().__init__("godot_physics", "godot_advanced", "coding")
    
    def generate(self) -> str:
        return """# Godot Physics & Collision Detection

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
"""


class GodotAnimationGenerator(KnowledgeGenerator):
    """Godot animation system and state machines."""
    
    def __init__(self):
        super().__init__("godot_animation", "godot_advanced", "coding")
    
    def generate(self) -> str:
        return """# Godot Animation System

## AnimationPlayer Node

### Basic Setup
```gdscript
# Create animation programmatically
var anim_player = AnimationPlayer.new()
add_child(anim_player)

var animation = Animation.new()
animation.length = 2.0

# Add track for position
var track_idx = animation.add_track(Animation.TYPE_VALUE)
animation.track_set_path(track_idx, "Sprite2D:position")
animation.track_insert_key(track_idx, 0.0, Vector2(0, 0))
animation.track_insert_key(track_idx, 1.0, Vector2(100, 0))
animation.track_insert_key(track_idx, 2.0, Vector2(0, 0))

anim_player.add_animation("move_cycle", animation)
anim_player.play("move_cycle")
```

### Animation Blending
```gdscript
# Smooth transition between animations
anim_player.play("walk")
await get_tree().create_timer(0.2).timeout
anim_player.play("run", 0.3)  # 0.3s blend time
```

## AnimationTree Node

### State Machine Setup
```gdscript
# In _ready()
var tree = $AnimationTree
tree.active = true
var state_machine = tree.get("parameters/playback")

# Transition based on state
func update_animation(velocity: Vector2):
    if velocity.length() > 0:
        state_machine.travel("running")
    else:
        state_machine.travel("idle")
```

### Blend Trees
```gdscript
# 2D blend for 8-directional movement
var blend2_node = AnimationNodeBlendSpace2D.new()
blend2_node.blend_mode = AnimationNodeBlendSpace2D.BLEND_MODE_INTERPOLATED

# Add points: right, up-right, up, etc.
blend2_node.add_point("walk_right", Vector2(1, 0), walk_right_anim)
blend2_node.add_point("walk_up", Vector2(0, 1), walk_up_anim)
blend2_node.add_point("walk_left", Vector2(-1, 0), walk_left_anim)
blend2_node.add_point("walk_down", Vector2(0, -1), walk_down_anim)

# Set parameters from code
tree.set("parameters/blend2/blend_position", velocity.normalized())
```

## Skeleton3D & 3D Animation

### IK (Inverse Kinematics)
```gdscript
# Godot 4.x IK setup
func setup_ik():
    var ik = SkeletonIK3D.new()
    ik.skeleton_node = $"../Skeleton3D"
    ik.enabled = true
    add_child(ik)
    
    # Configure chain (shoulder → elbow → wrist)
    ik.chain bone1_name = "UpperArm"
    ik.chain_bone2_name = "LowerArm"
    ik.chain_bone3_name = "Hand"
```

### Animation Events
```gdscript
# Add method calls at specific frames
func _on_animation_player_animation_changed(anim_name):
    var animation = $AnimationPlayer.get_animation(anim_name)
    
    # Add footstep sound at frame 0.5
    animation.track_insert_key(
        animation.find_track("audio_stream", Animation.TYPE_AUDIO),
        0.5,
        preload("res://sounds/footstep.wav")
    )
```

## Procedural Animation

### Wave Motion
```gdscript
@export var wave_speed: float = 2.0
@export var wave_amplitude: float = 10.0

func _process(delta):
    var time = Time.get_ticks_msec() / 1000.0
    $Sprite2D.offset.y = sin(time * wave_speed) * wave_amplitude
```

### Look At Target
```gdscript
func look_at_target(target: Vector2):
    var direction = target - global_position
    if direction.length() > 0.1:
        var angle = direction.angle()
        $Sprite2D.rotation = lerp_angle($Sprite2D.rotation, angle, 0.2)
```

## Common Animation Issues

### Popping Between Animations
**Solution:** Use blend times and ensure compatible poses
```gdscript
# Always specify blend time for smooth transitions
state_machine.travel("new_state", 0.2)
```

### Animation Speed Variation
```gdscript
# Normalize animation speed regardless of framerate
anim_player.speed_scale = 1.0
anim_player.seek(0, true)  # Reset to start
```

### Root Motion
```gdscript
# Extract motion from animation
var root_motion = anim_player.root_motion_delta
global_position += root_motion
```
"""


# Continue with more generators...
GENERATORS: List[KnowledgeGenerator] = [
    GodotPhysicsGenerator(),
    GodotAnimationGenerator(),
    # More will be added below
]


def main():
    parser = argparse.ArgumentParser(description="Ether Knowledge Expander")
    parser.add_argument("--category", type=str, help="Generate specific category")
    parser.add_argument("--list", action="store_true", help="List available generators")
    parser.add_argument("--output", type=str, default="knowledge_base", help="Output directory")
    
    args = parser.parse_args()
    
    if args.list:
        print("Available knowledge generators:")
        for gen in GENERATORS:
            print(f"  - {gen.name} ({gen.category}) [{gen.mode}]")
        return
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generated_count = 0
    for generator in GENERATORS:
        if args.category and generator.category != args.category:
            continue
        
        try:
            content = generator.generate()
            
            # Add metadata header
            metadata = (
                f"---\n"
                f"source: expander\n"
                f"generated: {datetime.now().isoformat()}\n"
                f"category: {generator.category}\n"
                f"mode: {generator.mode}\n"
                f"---\n\n"
            )
            
            output_file = output_dir / generator.get_filename()
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(metadata + content)
            
            print(f"✓ Generated {output_file}")
            generated_count += 1
            
        except Exception as e:
            print(f"❌ Failed to generate {generator.name}: {e}")
    
    print(f"\nGenerated {generated_count} knowledge files")


if __name__ == "__main__":
    main()
