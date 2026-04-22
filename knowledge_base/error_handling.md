---
source: expander
generated: 2026-04-22T17:34:06.614908
category: general_programming
mode: coding
---

# Error Handling Patterns

## Result Type Pattern
```gdscript
class Result:
    var success: bool
    var value: Variant
    var error: String
    
    static func ok(v) -> Result:
        var r = Result.new()
        r.success = true
        r.value = v
        return r
    
    static func err(msg) -> Result:
        var r = Result.new()
        r.success = false
        r.error = msg
        return r

func divide(a, b) -> Result:
    if b == 0:
        return Result.err("Division by zero")
    return Result.ok(a / b)
```

## Defensive Programming
```gdscript
func attack(target: Node, damage: int):
    assert(target != null, "Target cannot be null")
    assert(damage >= 0, "Damage must be non-negative")
    
    if not is_instance_valid(target):
        push_warning("Target already freed")
        return
    
    target.take_damage(damage)
```

## Logging Strategies
```gdscript
enum LogLevel { DEBUG, INFO, WARN, ERROR }

func log(level: LogLevel, msg: String):
    var timestamp = Time.get_datetime_string_from_system()
    print("[%s] %s: %s" % [timestamp, ["DBG","INF","WRN","ERR"][level], msg])
```
