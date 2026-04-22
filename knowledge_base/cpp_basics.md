---
source: cpp_basics
mode: coding
topics: c++, memory, pointers, smart pointers, RAII, modern c++
updated: 2026-04-22T14:42:07.214227
---

# C++ Programming Knowledge Base

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
