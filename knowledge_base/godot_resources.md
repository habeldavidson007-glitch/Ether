---
source: expander
generated: 2026-04-22T16:28:55.560181
category: godot_advanced
mode: coding
---

# Godot Resource System Mastery

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
