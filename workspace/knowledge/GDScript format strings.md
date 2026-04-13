---
id: "29d13b7635f0"
type: "knowledge"
title: "GDScript format strings"
tags:
  - scripting
  - example
source_type: "document"
source_file: "tutorials/scripting/gdscript/gdscript_format_string.rst"
sections: "32"
code_samples: "13"
created_at: "2026-04-08T09:05:24.753388"
---

# GDScript format strings

## Content Preview

.. _doc_gdscript_printf:

GDScript format strings
=======================

Godot offers multiple ways to dynamically change the contents of strings:

- Format strings: ``var string = "I have %s cats." % "3"``
- The ``String.format()`` method: ``var string = "I have {0} cats.".format([3])``
- String concatenation: ``var string = "I have " + str(3) + " cats."``

This page explains how to use format strings, and briefly explains the ``format()``
method and string concatenation.

Format strings
----


## Connections

- [[Core functions and types]] (incoming)
- [[GD0104_ The exported property is write-only]] (incoming)
- [[GDScript style guide]] (incoming)
- [[Page not found]] (incoming)
- [[C# basics]] (outgoing)
- [[Idle and Physics Processing]] (outgoing)
- [[Scene Unique Nodes]] (outgoing)
- [[Using TileMaps]] (outgoing)
- [[The GDExtension system]] (incoming)
- [[Getting started]] (incoming)
- [[Core functions and types]] (incoming)
- [[GDScript style guide]] (incoming)
- [[Ragdoll system]] (outgoing)
- [[Custom performance monitors]] (outgoing)
- [[Using the MeshDataTool]] (outgoing)
- [[C++ (godot-cpp)]] (outgoing)