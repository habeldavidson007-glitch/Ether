---
source: expander
generated: 2026-04-22T16:10:25.817545
category: cpp_advanced
mode: coding
---

# C++ Performance Patterns

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
