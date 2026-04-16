---
id: "0c43abf30d75"
type: "knowledge"
title: "Change scenes manually"
tags:
  - scripting
  - ui
source_type: "document"
source_file: "tutorials/scripting/change_scenes_manually.rst"
sections: "7"
code_samples: "0"
created_at: "2026-04-08T09:05:24.676065"
---

# Change scenes manually

## Content Preview

.. _doc_change_scenes_manually:

Change scenes manually
======================

Sometimes it helps to have more control over how you swap scenes around.
A :ref:`Viewport <class_Viewport>`'s child nodes will render to the image
it generates. This holds true even for nodes outside of the "current"
scene. Autoloads fall into this category, and also scenes which you
instantiate and add to the tree at runtime:

.. tabs::
 .. code-tab:: gdscript GDScript

    var simultaneous_scene = preload("res://le


## Connections

- [[Using the ObjectDB profiler]] (incoming)
- [[Custom drawing in 2D]] (incoming)
- [[Using Jolt Physics]] (incoming)
- [[Static typing in GDScript]] (incoming)
- [[Signed distance field global illumination (SDFGI)]] (outgoing)
- [[GDScript style guide]] (outgoing)
- [[Kinematic character (2D)]] (outgoing)
- [[Main build system_ Working with SCons]] (outgoing)
- [[GDScript documentation comments]] (incoming)
- [[Cross-language scripting]] (incoming)
- [[GDScript exported properties]] (incoming)
- [[Creating script templates]] (incoming)
- [[The GDExtension system]] (outgoing)
- [[Getting started]] (outgoing)
- [[Core functions and types]] (outgoing)
- [[GD0104_ The exported property is write-only]] (outgoing)