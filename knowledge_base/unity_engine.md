# Unity Engine Fundamentals
Updated: 2026-04-22

## Core Concepts

### GameObjects and Components
- GameObjects are containers
- Components add functionality (MonoBehaviour)
- Component-based architecture

### MonoBehaviour Lifecycle
```csharp
void Awake() { }      // Initialization
void Start() { }      // Before first frame
void Update() { }     // Every frame
void FixedUpdate() { } // Physics step
void OnDestroy() { }  // Cleanup
```

### Scripting in C#
- Strongly typed, compiled language
- Garbage collected
- Extensive standard library
- LINQ for data manipulation

### Asset Pipeline
- Import models, textures, audio
- Prefabs for reusable objects
- ScriptableObjects for data assets

### Physics System
- Rigidbody for physics simulation
- Colliders for collision detection
- Triggers for overlap events
