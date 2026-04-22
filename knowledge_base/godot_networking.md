---
source: expander
generated: 2026-04-22T17:33:58.376389
category: godot_advanced
mode: coding
---

# Godot Multiplayer & Networking

## High-Level API

### MultiplayerSpawner
```gdscript
var spawner = MultiplayerSpawner.new()
spawner.spawn_path = NodePath("World/Enemies")
add_child(spawner)

enemy.set_multiplayer_authority(1) # Server authority
spawner.add_spawnable_node(enemy)
```

## RPC (Remote Procedure Calls)
```gdscript
@rpc("any_peer", "call_local", "reliable")
func take_damage(amount: int, source_id: int):
    health -= amount
    if multiplayer.is_server():
        rpc("sync_health", health)

@rpc("authority", "unreliable")
func sync_health(new_health: int):
    health = new_health
```

## Connection Handling
```gdscript
var peer = ENetMultiplayerPeer.new()

# Host server
peer.create_server(1234, max_clients=32)
multiplayer.multiplayer_peer = peer

# Join client
peer.create_client("192.168.1.100", 1234)

# Signals
multiplayer.peer_connected.connect(_on_player_join)
```

## Authority & Prediction
- **Server Authority**: Validate all actions (anti-cheat)
- **Client Prediction**: Execute locally, reconcile later
- **Lag Compensation**: Store input history, rewind on mismatch
