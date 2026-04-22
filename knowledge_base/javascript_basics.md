---
source: javascript_basics
mode: coding
topics: javascript, async, promises, dom, es6
updated: 2026-04-22T14:42:07.214382
---

# JavaScript Knowledge Base

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
