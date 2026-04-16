---
id: "0162c9e7d1b6"
type: "knowledge"
title: "Idle and Physics Processing"
tags:
  - scripting
  - physics
source_type: "document"
source_file: "tutorials/scripting/idle_and_physics_processing.rst"
sections: "11"
code_samples: "0"
created_at: "2026-04-08T09:05:24.689384"
---

# Idle and Physics Processing

## Content Preview

.. _doc_idle_and_physics_processing:

Idle and Physics Processing
===========================

Games run in a loop. Each frame, you need to update the state of your game world
before drawing it on screen. Godot provides two virtual methods in the Node
class to do so: :ref:`Node._process() <class_Node_private_method__process>` and
:ref:`Node._physics_process() <class_Node_private_method__physics_process>`. If you
define either or both in a script, the engine will call them automatically.

There a


## Connections

- [[GDScript style guide]] (incoming)
- [[Page not found]] (incoming)
- [[GDScript format strings]] (incoming)
- [[C# basics]] (incoming)
- [[Scene Unique Nodes]] (outgoing)
- [[Using TileMaps]] (outgoing)
- [[C# signals]] (outgoing)
- [[Overridable functions]] (outgoing)
- [[Using Jolt Physics]] (incoming)
- [[Using SoftBody3D]] (incoming)
- [[Introduction]] (incoming)
- [[Rendering]] (incoming)
- [[Ragdoll system]] (outgoing)
- [[Using TileMaps]] (outgoing)
- [[Collision shapes (2D)]] (outgoing)
- [[Particle turbulence]] (outgoing)