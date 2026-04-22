---
source: expander
generated: 2026-04-22T16:04:16.776123
category: godot_advanced
mode: coding
---

# Godot Animation System

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
