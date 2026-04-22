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


# ============================================================================
# ADDITIONAL GENERATORS (10+ more specialized topics)
# ============================================================================

class GodotSignalsGenerator(KnowledgeGenerator):
    """Advanced Godot signals and communication patterns."""
    
    def __init__(self):
        super().__init__("godot_signals", "godot_advanced", "coding")
    
    def generate(self) -> str:
        return """# Godot Signals & Communication Patterns

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
"""


class GodotResourcesGenerator(KnowledgeGenerator):
    """Godot Resource system and data-driven design."""
    
    def __init__(self):
        super().__init__("godot_resources", "godot_advanced", "coding")
    
    def generate(self) -> str:
        return """# Godot Resource System Mastery

## What are Resources?
- Data containers saved as `.tres` or `.res` files
- Inherit from `Resource` class
- Support custom properties, export hints, nesting
- Reference-counted (automatic memory management)

## Creating Custom Resources

### Basic Resource Class
```gdscript
class_name ItemData extends Resource

@export var item_name: String
@export var icon: Texture2D
@export var stats: Dictionary = {"str": 0, "dex": 0}
@export_file("*.tscn") var scene_path: String
@export_enum("Common", "Rare", "Epic", "Legendary") var rarity: int
```

### Usage Patterns

#### 1. Data-Driven Item System
```gdscript
@export var items: Array[ItemData]

func get_item(index: int) -> ItemData:
    return items[index] if index < items.size() else null

func equip_item(item: ItemData):
    if item:
        apply_stats(item.stats)
```

#### 2. Dynamic Loading
```gdscript
var resource = load("res://data/items/sword.tres")
var new_resource = resource.duplicate() # Safe modification
```

#### 3. Nested Resources
```gdscript
class_name QuestData extends Resource
@export var title: String
@export var objectives: Array[ObjectiveData]
@export var rewards: Array[ItemData]
```

## Best Practices
- Use `@export_resource` for type safety (Godot 4.2+)
- Avoid loading large resources in `_ready()`; use threads
- Resources are reference-counted; manual `free()` rarely needed
- Use `take_over_path()` when replacing saved resources
"""


class CPPMemoryGenerator(KnowledgeGenerator):
    """C++ memory management for game development."""
    
    def __init__(self):
        super().__init__("cpp_memory", "cpp_advanced", "coding")
    
    def generate(self) -> str:
        return """# C++ Memory Management for Games

## Smart Pointers (Modern C++)

### Unique Pointer (Exclusive Ownership)
```cpp
std::unique_ptr<Player> player = std::make_unique<Player>();
player->update(); // Auto-deleted when out of scope

// Transfer ownership
std::unique_ptr<Player> ptr2 = std::move(player);
```

### Shared Pointer (Reference Counted)
```cpp
std::shared_ptr<Texture> tex = std::make_shared<Texture>("path.png");
auto copy = tex; // Reference count increases
// Auto-deleted when last reference dies
```

### Weak Pointer (Non-Owning Observer)
```cpp
std::weak_ptr<Player> weak = player;
if(auto locked = weak.lock()) {
    locked->take_damage(10);
}
```

## RAII Pattern

### Resource Acquisition Is Initialization
```cpp
class FileHandle {
    FILE* file;
public:
    FileHandle(const char* path) { file = fopen(path, "r"); }
    ~FileHandle() { if(file) fclose(file); }
    // Disable copy
    FileHandle(const FileHandle&) = delete;
};
```

## Custom Allocators

### Stack Allocator for Temporary Objects
```cpp
class StackAllocator {
    char* buffer;
    size_t offset = 0;
public:
    void* allocate(size_t size) {
        void* ptr = buffer + offset;
        offset += size;
        return ptr;
    }
    void reset() { offset = 0; } // Free all at once
};
```

## Common Pitfalls
- **Dangling Pointers**: Check lifetime before using raw pointers
- **Circular References**: Use `weak_ptr` to break cycles
- **Mixing Allocators**: Don't `delete` custom allocator memory
- **Premature Optimization**: Profile first!
"""


class CPPPerformanceGenerator(KnowledgeGenerator):
    """C++ performance optimization patterns."""
    
    def __init__(self):
        super().__init__("cpp_performance", "cpp_advanced", "coding")
    
    def generate(self) -> str:
        return """# C++ Performance Patterns

## Data-Oriented Design

### Structure of Arrays (Cache Friendly)
```cpp
// ❌ Bad: Array of Structures
struct Entity { Vec3 pos; Vec3 vel; bool active; };
std::vector<Entity> entities;

// ✅ Good: Structure of Arrays
struct EntityArray {
    std::vector<Vec3> positions;
    std::vector<Vec3> velocities;
    std::vector<bool> active;
};
```

## Move Semantics
```cpp
// Avoid copies
std::string process(std::string&& input) {
    return input + "_processed";
}
auto result = process(std::move(large_string));
```

## Inline & Constexpr
```cpp
inline float clamp(float v, float min, float max) {
    return v < min ? min : (v > max ? max : v);
}

constexpr int factorial(int n) {
    return n <= 1 ? 1 : n * factorial(n - 1);
}
```

## Profiling Tools
- **Valgrind**: Memory leak detection
- **perf** (Linux): CPU profiling
- **Visual Studio Profiler**: Windows tool
- **Tracy**: Real-time game profiler (recommended)
"""


class ShaderBasicsGenerator(KnowledgeGenerator):
    """Godot shader programming fundamentals."""
    
    def __init__(self):
        super().__init__("shader_basics", "godot_advanced", "coding")
    
    def generate(self) -> str:
        return """# Godot Shader Language (GDShader)

## Shader Types
- **Spatial**: 3D lighting, materials
- **CanvasItem**: 2D sprites, UI effects
- **Particles**: GPU particle behavior

## Basic Spatial Shader
```glsl
shader_type spatial;

uniform vec4 albedo : source_color;
uniform float metallic;
uniform float roughness;

void vertex() {
    UV = UV * 2.0; // Tile texture
}

void fragment() {
    ALBEDO = albedo.rgb;
    METALLIC = metallic;
    ROUGHNESS = roughness;
}
```

## Common Effects

### Dissolve Effect
```glsl
uniform sampler2D noise_texture;
uniform float dissolve_amount : hint_range(0, 1);

void fragment() {
    float noise = texture(noise_texture, UV).r;
    if (noise < dissolve_amount) discard;
    ALBEDO = mix(albedo, vec3(1.0), 
                 smoothstep(dissolve_amount-0.1, dissolve_amount, noise));
}
```

### Fresnel Outline
```glsl
uniform vec4 outline_color : source_color;

void fragment() {
    float fresnel = dot(NORMAL, VIEW);
    float outline = smoothstep(0.2, 0.0, fresnel);
    ALBEDO = mix(albedo, outline_color.rgb, outline);
}
```

## Performance Tips
- Use precision hints: `lowp`, `mediump`, `highp`
- Avoid branching; use `mix()` or `step()`
- Minimize texture samples
- Use `INSTANCE_CUSTOM` for batching
"""


class NetworkingGenerator(KnowledgeGenerator):
    """Godot multiplayer and networking."""
    
    def __init__(self):
        super().__init__("godot_networking", "godot_advanced", "coding")
    
    def generate(self) -> str:
        return """# Godot Multiplayer & Networking

## High-Level API

### MultiplayerSpawner
```gdscript
var spawner = MultiplayerSpawner.new()
spawner.spawn_path = NodePath("World/Enemies")
add_child(spawner)

enemy.set_multiplayer_authority(1) # Server authority
spawner.add_spawnable_node(enemy)
```

## RPC (Remote Procedure Calls)
```gdscript
@rpc("any_peer", "call_local", "reliable")
func take_damage(amount: int, source_id: int):
    health -= amount
    if multiplayer.is_server():
        rpc("sync_health", health)

@rpc("authority", "unreliable")
func sync_health(new_health: int):
    health = new_health
```

## Connection Handling
```gdscript
var peer = ENetMultiplayerPeer.new()

# Host server
peer.create_server(1234, max_clients=32)
multiplayer.multiplayer_peer = peer

# Join client
peer.create_client("192.168.1.100", 1234)

# Signals
multiplayer.peer_connected.connect(_on_player_join)
```

## Authority & Prediction
- **Server Authority**: Validate all actions (anti-cheat)
- **Client Prediction**: Execute locally, reconcile later
- **Lag Compensation**: Store input history, rewind on mismatch
"""


class DesignPatternsGameGenerator(KnowledgeGenerator):
    """Game-specific design patterns."""
    
    def __init__(self):
        super().__init__("design_patterns_game", "architecture", "coding")
    
    def generate(self) -> str:
        return """# Game Design Patterns

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
"""


class AsyncProgrammingGenerator(KnowledgeGenerator):
    """Asynchronous programming patterns."""
    
    def __init__(self):
        super().__init__("async_programming", "general_programming", "coding")
    
    def generate(self) -> str:
        return """# Asynchronous Programming Patterns

## Godot Async/Await
```gdscript
# Modern await syntax (Godot 4.x)
func load_level_async(path: String):
    var resource = await ResourceLoader.load_threaded_request(path)
    $LoadingScreen.hide()
    return resource

# Sequential awaits
func fetch_data():
    var user = await api.get_user(id)
    var posts = await api.get_posts(user.id)
    return {"user": user, "posts": posts}

# Parallel awaits
func fetch_parallel():
    var results = await [api.get_a(), api.get_b(), api.get_c()]
```

## Error Handling
```gdscript
func safe_fetch(url):
    try:
        return await http.get(url)
    catch err:
        print("Fetch failed: ", err)
        return null

# Retry pattern
func fetch_with_retry(url, retries=3):
    for i in range(retries):
        var result = await safe_fetch(url)
        if result: return result
        await get_tree().create_timer(1.0).timeout
    return null
```

## Best Practices
- Always await in async functions
- Use `try/catch` for I/O operations
- Cancel pending operations on scene exit
"""


class ErrorHandlingGenerator(KnowledgeGenerator):
    """Error handling and robustness patterns."""
    
    def __init__(self):
        super().__init__("error_handling", "general_programming", "coding")
    
    def generate(self) -> str:
        return """# Error Handling Patterns

## Result Type Pattern
```gdscript
class Result:
    var success: bool
    var value: Variant
    var error: String
    
    static func ok(v) -> Result:
        var r = Result.new()
        r.success = true
        r.value = v
        return r
    
    static func err(msg) -> Result:
        var r = Result.new()
        r.success = false
        r.error = msg
        return r

func divide(a, b) -> Result:
    if b == 0:
        return Result.err("Division by zero")
    return Result.ok(a / b)
```

## Defensive Programming
```gdscript
func attack(target: Node, damage: int):
    assert(target != null, "Target cannot be null")
    assert(damage >= 0, "Damage must be non-negative")
    
    if not is_instance_valid(target):
        push_warning("Target already freed")
        return
    
    target.take_damage(damage)
```

## Logging Strategies
```gdscript
enum LogLevel { DEBUG, INFO, WARN, ERROR }

func log(level: LogLevel, msg: String):
    var timestamp = Time.get_datetime_string_from_system()
    print("[%s] %s: %s" % [timestamp, ["DBG","INF","WRN","ERR"][level], msg])
```
"""


class GodotOptimizationGenerator(KnowledgeGenerator):
    """Godot performance optimization guide."""
    
    def __init__(self):
        super().__init__("godot_optimization", "godot_advanced", "coding")
    
    def generate(self) -> str:
        return """# Godot Performance Optimization

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
"""


class TroubleshootingGenerator(KnowledgeGenerator):
    """Common Godot troubleshooting guide."""
    
    def __init__(self):
        super().__init__("troubleshooting_godot", "godot_advanced", "mixed")
    
    def generate(self) -> str:
        return """# Godot Troubleshooting Guide

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
"""


# ============================================================================
# GENERATOR REGISTRY
# ============================================================================

GENERATORS: List[KnowledgeGenerator] = [
    # Godot Advanced (5)
    GodotPhysicsGenerator(),
    GodotAnimationGenerator(),
    GodotSignalsGenerator(),
    GodotResourcesGenerator(),
    GodotOptimizationGenerator(),
    
    # C++ Advanced (2)
    CPPMemoryGenerator(),
    CPPPerformanceGenerator(),
    
    # Shaders & Networking (2)
    ShaderBasicsGenerator(),
    NetworkingGenerator(),
    
    # Architecture & Patterns (2)
    DesignPatternsGameGenerator(),
    TroubleshootingGenerator(),
    
    # General Programming (2)
    AsyncProgrammingGenerator(),
    ErrorHandlingGenerator(),
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
