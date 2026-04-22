# C++ Fundamentals
Updated: 2026-04-22

## Memory and Ownership
- Prefer RAII for deterministic cleanup
- Use smart pointers (`std::unique_ptr`, `std::shared_ptr`) when ownership is shared
- Avoid raw `new`/`delete` in gameplay code

## Core Practices
- Keep headers minimal and include only what you use
- Use `const` correctness and references where possible
- Favor composition and small classes

## Topic Index
allocator, constexpr, constructor, coroutine, copyelision, deadlock, destructor, encapsulation, enumclass, forwarding, functor, inheritance, iterator, lambda, linkage, metaprogramming, moveonly, mutex, noexcept, polymorphism, preprocessor, rvalue, semaphore, smartpointer, stacktrace, stdvector, templates, threadlocal, tuple, typeerasure, unorderedmap, variant, virtualtable
