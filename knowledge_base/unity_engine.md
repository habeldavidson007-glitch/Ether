---
source: unity_engine
mode: coding
topics: unity, c#, monobehaviour, components, coroutines
updated: 2026-04-22T14:42:07.214335
---

# Unity Engine Knowledge Base

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
