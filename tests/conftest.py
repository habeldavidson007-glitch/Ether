"""
Test configuration and fixtures for Ether test suite.
"""
import pytest
import sys
import asyncio
import inspect
from pathlib import Path

# Add the workspace root to the path so we can import ether modules
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


def pytest_configure(config):
    """Register custom markers used by the test suite."""
    config.addinivalue_line(
        "markers",
        "asyncio: run test using asyncio without requiring external plugins"
    )


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    """
    Lightweight async test runner fallback.
    Runs coroutine test functions and tests marked with @pytest.mark.asyncio.
    """
    is_async_test = inspect.iscoroutinefunction(pyfuncitem.obj)
    has_asyncio_marker = pyfuncitem.get_closest_marker("asyncio") is not None

    if not (is_async_test or has_asyncio_marker):
        return None

    testargs = {
        arg: pyfuncitem.funcargs[arg]
        for arg in pyfuncitem._fixtureinfo.argnames
    }
    asyncio.run(pyfuncitem.obj(**testargs))
    return True


@pytest.fixture
def sample_godot_project(tmp_path):
    """Create a minimal Godot project structure for testing."""
    # Create project.godot
    project_file = tmp_path / "project.godot"
    project_file.write_text("""
; Engine configuration file.
; It's best edited using the editor UI and not directly,
; since the parameters that go here are not all obvious.

config_version=5

[application]

config/name="Test Project"
run/main_scene="res://scenes/main.tscn"
config/features=PackedStringArray("4.2", "Forward Plus")

[rendering]

renderer/rendering_method="forward_plus"
""")
    
    # Create scenes directory
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    
    # Create a simple scene
    scene_file = scenes_dir / "main.tscn"
    scene_file.write_text("""
[gd_scene load_steps=2 format=3 uid="uid://test123"]

[ext_resource type="Script" path="res://scripts/player.gd" id="1"]

[node name="Player" type="CharacterBody2D"]
script = ExtResource("1")
""")
    
    # Create scripts directory
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    
    # Create a simple GDScript
    script_file = scripts_dir / "player.gd"
    script_file.write_text("""
extends CharacterBody2D

var speed = 400.0
var jump_velocity = -400.0

func get_input():
    return Input.get_vector("left", "right", "up", "down")

func _physics_process(delta):
    velocity = get_input() * speed
    move_and_slide()
""")
    
    return tmp_path


@pytest.fixture
def sample_gdscript_code():
    """Sample GDScript code for testing analysis."""
    return """
extends CharacterBody2D

@export var speed: float = 400.0
@export var jump_velocity: float = -400.0

var gravity = ProjectSettings.get_setting("physics/2d/default_gravity")

func get_input() -> Vector2:
    return Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")

func _physics_process(delta: float) -> void:
    if not is_on_floor():
        velocity.y += gravity * delta
    
    if Input.is_action_just_pressed("ui_accept") and is_on_floor():
        velocity.y = jump_velocity
    
    velocity.x = get_input().x * speed
    move_and_slide()
"""


@pytest.fixture
def sample_tscn_content():
    """Sample TSCN scene content for testing."""
    return """
[gd_scene load_steps=3 format=3 uid="uid://test123"]

[ext_resource type="Script" path="res://scripts/player.gd" id="1"]
[ext_resource type="PackedScene" path="res://scenes/enemy.tscn" id="2"]

[node name="Player" type="CharacterBody2D"]
position = Vector2(100, 100)
script = ExtResource("1")

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
shape = SubResource("RectangleShape2D")

[node name="Sprite2D" type="Sprite2D" parent="."]
texture = ExtResource("Texture2D")
"""


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "response": "This is a mock LLM response for testing purposes.",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }
