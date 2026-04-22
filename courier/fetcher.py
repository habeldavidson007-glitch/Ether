"""
Ether Courier - Knowledge Base Updater
=======================================
Purpose: Fetch and update knowledge base from various sources.

Features:
- 7 pre-configured knowledge sources
- Godot, C++, Unreal, Unity, JavaScript, Design Patterns, General Facts
- Run separately to avoid runtime overhead
- Easy to extend with new sources

Usage:
    # Update all knowledge sources
    python courier/fetcher.py
    
    # Update specific sources only
    python courier/fetcher.py --sources godot_docs cpp_basics
    
    # Specify custom output directory
    python courier/fetcher.py --output /path/to/knowledge
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class KnowledgeSource:
    """Base class for knowledge sources."""
    
    def __init__(self, name: str, description: str, mode: str = "mixed"):
        self.name = name
        self.description = description
        self.mode = mode  # 'coding', 'general', or 'mixed'
    
    def fetch(self) -> str:
        """Fetch content from source. Override in subclasses."""
        raise NotImplementedError
    
    def get_topics(self) -> List[str]:
        """Extract topics from content. Override for custom extraction."""
        return []


class GodotSource(KnowledgeSource):
    """Godot Engine documentation and best practices."""
    
    def __init__(self):
        super().__init__(
            "godot_engine",
            "Godot Engine documentation, GDScript patterns, and node system",
            mode="coding"
        )
    
    def fetch(self) -> str:
        """Generate comprehensive Godot knowledge content."""
        return """# Godot Engine Knowledge Base

## Core Concepts

### Scene System
Godot uses a scene-based architecture where everything is a Node. Scenes can be nested to create complex hierarchies.

**Key Points:**
- Everything inherits from Node
- Scenes are reusable components
- Tree structure with parent-child relationships
- Signals for communication between nodes

### GDScript Basics
GDScript is Python-like language optimized for Godot.

```gdscript
extends Node2D

@export var speed: float = 100.0
var velocity: Vector2 = Vector2.ZERO

func _process(delta: float) -> void:
    velocity = Input.get_axis("ui_left", "ui_right") * speed
    position += velocity * delta
```

### Common Patterns

#### Singleton (Autoload)
1. Create a script
2. Go to Project → Project Settings → Autoload
3. Add your script as autoload
4. Access globally by name

#### State Machine
Use for character states (idle, walk, jump, attack).

#### Signal-Based Communication
Decouple nodes using signals instead of direct references.

### Performance Tips
- Use `_physics_process` for physics, `_process` for visuals
- Batch draw calls when possible
- Object pooling for frequently spawned objects
- Use `yield` or await for async operations

### Memory Management
- Godot handles most memory automatically
- Use `queue_free()` to remove nodes
- Be careful with circular references
- Disconnect signals when nodes are freed

## Common Issues & Solutions

### Movement Issues
**Problem:** Character moves differently on different framerates
**Solution:** Always multiply by delta in `_process` or use `_physics_process`

### Signal Connection Errors
**Problem:** "Nonexistent signal" errors
**Solution:** Check signal names, ensure emitter exists before connecting

### Export Variables Not Showing
**Problem:** @export variables don't appear in inspector
**Solution:** Save script, check variable type is exportable

## Best Practices
1. Keep scenes focused and reusable
2. Use composition over inheritance
3. Name nodes and variables clearly
4. Organize project with folders
5. Use version control
6. Test on target platforms early
"""
    
    def get_topics(self) -> List[str]:
        return ["godot", "gdscript", "game development", "nodes", "scenes", "signals"]


class CPPSource(KnowledgeSource):
    """C++ programming fundamentals."""
    
    def __init__(self):
        super().__init__(
            "cpp_basics",
            "C++ memory management, pointers, OOP, and modern features",
            mode="coding"
        )
    
    def fetch(self) -> str:
        return """# C++ Programming Knowledge Base

## Memory Management

### Manual Memory (Legacy)
```cpp
int* ptr = new int(42);
// ... use ptr ...
delete ptr;  // Must manually delete!
```

### Smart Pointers (Modern C++)
```cpp
#include <memory>

// Unique pointer (exclusive ownership)
std::unique_ptr<int> unique = std::make_unique<int>(42);

// Shared pointer (reference counted)
std::shared_ptr<int> shared = std::make_shared<int>(42);

// Weak pointer (non-owning reference)
std::weak_ptr<int> weak = shared;
```

### RAII Pattern
Resource Acquisition Is Initialization - resources tied to object lifetime.

```cpp
class FileHandler {
    FILE* file;
public:
    FileHandler(const char* path) {
        file = fopen(path, "r");  // Acquire in constructor
    }
    ~FileHandler() {
        fclose(file);  // Release in destructor
    }
};
```

## Common Memory Issues

### Memory Leaks
**Cause:** Forgetting to delete allocated memory
**Solution:** Use smart pointers or RAII

### Dangling Pointers
**Cause:** Using pointer after memory is freed
**Solution:** Set pointers to nullptr after delete, use smart pointers

### Double Free
**Cause:** Deleting same memory twice
**Solution:** Track ownership, use smart pointers

## Modern C++ Features

### Auto Keyword
```cpp
auto x = 42;           // int
auto y = 3.14;         // double
auto vec = std::vector<int>{};
```

### Range-based For Loops
```cpp
std::vector<int> nums = {1, 2, 3, 4, 5};
for (const auto& num : nums) {
    std::cout << num << std::endl;
}
```

### Lambda Expressions
```cpp
auto add = [](int a, int b) { return a + b; };
int result = add(2, 3);  // 5
```

## Best Practices
1. Prefer smart pointers over raw pointers
2. Use const correctness
3. Follow RAII for resource management
4. Use move semantics for efficiency
5. Avoid premature optimization
6. Write exception-safe code
"""
    
    def get_topics(self) -> List[str]:
        return ["c++", "memory", "pointers", "smart pointers", "RAII", "modern c++"]


class UnrealSource(KnowledgeSource):
    """Unreal Engine fundamentals."""
    
    def __init__(self):
        super().__init__(
            "unreal_engine",
            "Unreal Engine, Blueprints, C++, and game development",
            mode="coding"
        )
    
    def fetch(self) -> str:
        return """# Unreal Engine Knowledge Base

## Core Architecture

### UObject System
- All Unreal objects inherit from UObject
- Built-in reflection and serialization
- Garbage collection handled automatically

### Actor Components
- Actors are world objects
- Components add functionality
- Component-based architecture

### Blueprint Visual Scripting
- Node-based scripting system
- Great for designers and rapid prototyping
- Can call C++ functions

## C++ in Unreal

### Key Macros
```cpp
UCLASS()
class AMyActor : public AActor {
    GENERATED_BODY()
    
    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    float MyVariable;
    
    UFUNCTION(BlueprintCallable)
    void MyFunction();
};
```

### Property Specifiers
- `EditAnywhere`: Editable in editor
- `BlueprintReadWrite`: Accessible from Blueprints
- `Replicated`: Network replication
- `SaveGame`: Saved to save games

## Best Practices
1. Use C++ for performance-critical code
2. Use Blueprints for design iteration
3. Follow Unreal's naming conventions
4. Use smart pointers (TSharedPtr, TUniquePtr)
5. Understand Unreal's garbage collection
"""
    
    def get_topics(self) -> List[str]:
        return ["unreal", "blueprints", "uobject", "actors", "game development"]


class UnitySource(KnowledgeSource):
    """Unity Engine fundamentals."""
    
    def __init__(self):
        super().__init__(
            "unity_engine",
            "Unity Engine, C#, components, and game development",
            mode="coding"
        )
    
    def fetch(self) -> str:
        return """# Unity Engine Knowledge Base

## Component System

### MonoBehaviour Lifecycle
```csharp
void Awake() { }      // Initialize before Start
void Start() { }      // Initialize before first frame
void Update() { }     // Every frame
void FixedUpdate() { } // Physics updates
void OnDestroy() { }  // Cleanup
```

### Coroutines
```csharp
IEnumerator MyCoroutine() {
    yield return null;  // Wait one frame
    yield return new WaitForSeconds(1f);
    yield return new WaitForEndOfFrame();
}
```

## Common Patterns

### Singleton Pattern
```csharp
public class GameManager : MonoBehaviour {
    public static GameManager Instance { get; private set; }
    
    void Awake() {
        if (Instance == null) Instance = this;
        else Destroy(gameObject);
    }
}
```

### Object Pooling
```csharp
public class ObjectPool : MonoBehaviour {
    [SerializeField] GameObject prefab;
    Queue<GameObject> pool = new Queue<GameObject>();
    
    public GameObject Get() {
        return pool.Count > 0 ? pool.Dequeue() : Instantiate(prefab);
    }
    
    public void Return(GameObject obj) {
        obj.SetActive(false);
        pool.Enqueue(obj);
    }
}
```

## Performance Tips
1. Use object pooling for frequent instantiate/destroy
2. Cache component references
3. Use FixedUpdate for physics
4. Minimize allocations in Update
5. Use Profiler to find bottlenecks
"""
    
    def get_topics(self) -> List[str]:
        return ["unity", "c#", "monobehaviour", "components", "coroutines"]


class JavaScriptSource(KnowledgeSource):
    """JavaScript fundamentals."""
    
    def __init__(self):
        super().__init__(
            "javascript_basics",
            "JavaScript, async programming, DOM manipulation, and modern ES6+",
            mode="coding"
        )
    
    def fetch(self) -> str:
        return """# JavaScript Knowledge Base

## Modern JavaScript (ES6+)

### Arrow Functions
```javascript
const add = (a, b) => a + b;
const multiply = (a, b) => {
    return a * b;
};
```

### Destructuring
```javascript
const { name, age } = person;
const [first, second] = array;
```

### Async/Await
```javascript
async function fetchData() {
    try {
        const response = await fetch(url);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error(error);
    }
}
```

## Common Pitfalls

### This Binding
```javascript
// Problem: this loses context
obj.method();  // this = obj
const fn = obj.method;
fn();  // this = window/undefined

// Solution: arrow functions or bind
const bound = obj.method.bind(obj);
```

### Event Loop
- Synchronous code runs first
- Microtasks (Promises) run next
- Macrotasks (setTimeout) run after

## Best Practices
1. Use const/let instead of var
2. Prefer async/await over callbacks
3. Use template literals
4. Handle errors properly
5. Use strict mode
"""
    
    def get_topics(self) -> List[str]:
        return ["javascript", "async", "promises", "dom", "es6"]


class DesignPatternsSource(KnowledgeSource):
    """Software design patterns."""
    
    def __init__(self):
        super().__init__(
            "design_patterns",
            "Common software design patterns and architectural principles",
            mode="coding"
        )
    
    def fetch(self) -> str:
        return """# Design Patterns Knowledge Base

## Creational Patterns

### Singleton
Ensures only one instance exists.
```python
class Singleton:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**Use when:** Need single point of access (config, logger)
**Caution:** Can make testing difficult

### Factory
Creates objects without specifying exact class.
```python
class EnemyFactory:
    def create_enemy(self, enemy_type):
        if enemy_type == "goblin":
            return Goblin()
        elif enemy_type == "dragon":
            return Dragon()
```

## Structural Patterns

### Adapter
Makes incompatible interfaces work together.

### Decorator
Adds behavior dynamically without subclassing.

## Behavioral Patterns

### Observer
One-to-many dependency (publish-subscribe).

### Strategy
Encapsulates interchangeable algorithms.

## SOLID Principles

1. **Single Responsibility**: One reason to change
2. **Open/Closed**: Open for extension, closed for modification
3. **Liskov Substitution**: Subtypes must be substitutable
4. **Interface Segregation**: Many specific interfaces > one general
5. **Dependency Inversion**: Depend on abstractions, not concretions

## When to Use Patterns
- Don't force patterns prematurely
- Let needs emerge from code
- Refactor to patterns when duplication appears
"""
    
    def get_topics(self) -> List[str]:
        return ["design patterns", "singleton", "factory", "solid", "architecture"]


class GeneralFactsSource(KnowledgeSource):
    """General knowledge and facts."""
    
    def __init__(self):
        super().__init__(
            "general_facts",
            "General knowledge, trivia, and lifestyle information",
            mode="general"
        )
    
    def fetch(self) -> str:
        return """# General Facts Knowledge Base

## Health & Wellness

### Healthy Breakfast Options
- Oatmeal with fruits and nuts
- Greek yogurt with berries
- Eggs with whole grain toast
- Smoothie with protein powder

### Productivity Tips
- Pomodoro technique (25 min work, 5 min break)
- Two-minute rule (if <2 min, do it now)
- Time blocking for deep work
- Regular breaks improve focus

## Technology Trends

### AI & Machine Learning
- Generative AI for content creation
- LLMs for natural language tasks
- Computer vision applications
- Ethical AI considerations

### Software Development
- Remote/hybrid work standard
- Low-code/no-code platforms growing
- DevOps and CI/CD essential
- Security-first development

## Learning Strategies

### Effective Learning
- Spaced repetition for memory
- Active recall over passive reading
- Teach others to reinforce knowledge
- Practice projects over tutorials

### Skill Development
- Focus on fundamentals first
- Build progressively harder projects
- Join communities for feedback
- Consistent daily practice beats cramming
"""
    
    def get_topics(self) -> List[str]:
        return ["health", "productivity", "learning", "technology", "lifestyle"]


class KnowledgeFetcher:
    """Main fetcher orchestrator."""
    
    def __init__(self, output_dir: str = "knowledge_base"):
        self.output_dir = Path(output_dir)
        self.sources: Dict[str, KnowledgeSource] = {}
        self.register_default_sources()
    
    def register_default_sources(self):
        """Register all default knowledge sources."""
        sources = [
            GodotSource(),
            CPPSource(),
            UnrealSource(),
            UnitySource(),
            JavaScriptSource(),
            DesignPatternsSource(),
            GeneralFactsSource(),
        ]
        
        for source in sources:
            self.sources[source.name] = source
    
    def fetch_all(self, force: bool = False) -> Dict[str, bool]:
        """Fetch from all registered sources."""
        results = {}
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        for name, source in self.sources.items():
            results[name] = self.fetch_source(name, force)
        
        return results
    
    def fetch_source(self, name: str, force: bool = False) -> bool:
        """Fetch from a specific source."""
        if name not in self.sources:
            print(f"❌ Unknown source: {name}")
            return False
        
        source = self.sources[name]
        output_file = self.output_dir / f"{name}.md"
        
        # Skip if exists and not forced
        if output_file.exists() and not force:
            print(f"⏭️  Skipping {name} (already exists)")
            return True
        
        try:
            print(f"📥 Fetching {source.description}...")
            content = source.fetch()
            
            # Add metadata header
            metadata = f"""---
source: {source.name}
mode: {source.mode}
topics: {', '.join(source.get_topics())}
updated: {datetime.now().isoformat()}
---

"""
            output_file.write_text(metadata + content, encoding='utf-8')
            print(f"✅ Saved {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error fetching {name}: {e}")
            return False
    
    def list_sources(self):
        """List all available sources."""
        print("\nAvailable Knowledge Sources:")
        print("=" * 50)
        for name, source in self.sources.items():
            print(f"  {name:20} [{source.mode:7}] - {source.description}")
        print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Ether Knowledge Base Fetcher")
    parser.add_argument("--sources", nargs="+", help="Specific sources to fetch")
    parser.add_argument("--output", default="knowledge_base", help="Output directory")
    parser.add_argument("--force", action="store_true", help="Force re-fetch existing files")
    parser.add_argument("--list", action="store_true", help="List available sources")
    
    args = parser.parse_args()
    
    fetcher = KnowledgeFetcher(output_dir=args.output)
    
    if args.list:
        fetcher.list_sources()
        return
    
    if args.sources:
        results = {}
        for source_name in args.sources:
            results[source_name] = fetcher.fetch_source(source_name, args.force)
    else:
        results = fetcher.fetch_all(args.force)
    
    # Summary
    print("\n" + "=" * 50)
    print("Fetch Summary:")
    successful = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"  {successful}/{total} sources fetched successfully")
    print("=" * 50)


if __name__ == "__main__":
    main()
