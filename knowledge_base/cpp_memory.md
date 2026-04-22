---
source: expander
generated: 2026-04-22T16:28:55.560260
category: cpp_advanced
mode: coding
---

# C++ Memory Management for Games

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
