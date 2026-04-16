---
id: "902ed43e7b34"
type: "knowledge"
title: "Scene Unique Nodes"
tags:
  - scripting
  - ui
source_type: "document"
source_file: "tutorials/scripting/scene_unique_nodes.rst"
sections: "14"
code_samples: "1"
created_at: "2026-04-08T09:05:24.689701"
---

# Scene Unique Nodes

## Content Preview

.. _doc_scene_unique_nodes:

Scene Unique Nodes
==================

Introduction
------------

Using ``get_node()`` to reference nodes from a script can sometimes be fragile.
If you move a button in a UI scene from one panel to another, the button's node
path changes, and if a script uses ``get_node()`` with a hard-coded node path,
the script will not be able to find the button anymore.

In situations like this, the node can be turned into a scene
unique node to avoid having to update the script


## Connections

- [[ParticleProcessMaterial 2D Usage]] (incoming)
- [[Cross-language scripting]] (incoming)
- [[Mesh level of detail (LOD)]] (incoming)
- [[Godot Docs – _master_ branch]] (incoming)
- [[Environment and post-processing]] (outgoing)
- [[Collision shapes (2D)]] (outgoing)
- [[3D Particle system properties]] (outgoing)
- [[Reflection probes]] (outgoing)
- [[Page not found]] (incoming)
- [[GDScript format strings]] (incoming)
- [[C# basics]] (incoming)
- [[Idle and Physics Processing]] (incoming)
- [[Using TileMaps]] (outgoing)
- [[C# signals]] (outgoing)
- [[Overridable functions]] (outgoing)
- [[Using ImmediateMesh]] (outgoing)