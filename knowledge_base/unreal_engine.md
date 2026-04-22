---
source: unreal_engine
mode: coding
topics: unreal, blueprints, uobject, actors, game development
updated: 2026-04-22T14:42:07.214285
---

# Unreal Engine Knowledge Base

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
