---
source: expander
generated: 2026-04-22T16:10:25.817747
category: general_programming
mode: coding
---

# Asynchronous Programming Patterns

## Godot Async/Await
```gdscript
# Modern await syntax (Godot 4.x)
func load_level_async(path: String):
    var resource = await ResourceLoader.load_threaded_request(path)
    $LoadingScreen.hide()
    return resource

# Sequential awaits
func fetch_data():
    var user = await api.get_user(id)
    var posts = await api.get_posts(user.id)
    return {"user": user, "posts": posts}

# Parallel awaits
func fetch_parallel():
    var results = await [api.get_a(), api.get_b(), api.get_c()]
```

## Error Handling
```gdscript
func safe_fetch(url):
    try:
        return await http.get(url)
    catch err:
        print("Fetch failed: ", err)
        return null

# Retry pattern
func fetch_with_retry(url, retries=3):
    for i in range(retries):
        var result = await safe_fetch(url)
        if result: return result
        await get_tree().create_timer(1.0).timeout
    return null
```

## Best Practices
- Always await in async functions
- Use `try/catch` for I/O operations
- Cancel pending operations on scene exit
