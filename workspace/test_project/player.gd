extends CharacterBody2D

# Global state variables (anti-pattern test)
var health := 100
var score := 0
var level := 1
var inventory := []
var is_alive := true
var has_weapon := false
var speed := 300.0
var jump_strength := -400.0
var gravity := 980.0
var can_double_jump := false
var dash_cooldown := 0.0

func _ready():
    pass

func _process(delta):
    # Too much logic in _process (anti-pattern)
    var input_direction = Input.get_axis("ui_left", "ui_right")
    velocity.x = input_direction * speed
    
    if not is_on_floor():
        velocity.y += gravity * delta
    
    if Input.is_action_just_pressed("ui_accept") and is_on_floor():
        velocity.y = jump_strength
    
    # More processing logic
    if health <= 0:
        is_alive = false
        queue_free()
    
    # Even more logic
    score += int(delta * 10)
    level = score / 1000 + 1
    
    # Update UI
    var ui = get_node("/root/Game/UI")
    if ui:
        ui.update_health(health)
        ui.update_score(score)
    
    # Check for powerups
    var powerups = get_tree().get_nodes_in_group("powerups")
    for powerup in powerups:
        if global_position.distance_to(powerup.global_position) < 50:
            apply_powerup(powerup.type)
    
    # Handle dash
    if dash_cooldown > 0:
        dash_cooldown -= delta
    
    # Handle animations
    if input_direction != 0:
        $Sprite.flip_h = input_direction < 0

func apply_powerup(type):
    match type:
        "speed":
            speed += 100
        "health":
            health += 25
        "weapon":
            has_weapon = true

func take_damage(amount):
    health -= amount
    if health <= 0:
        die()

func die():
    is_alive = false
    emit_signal("died")
    queue_free()

signal died
