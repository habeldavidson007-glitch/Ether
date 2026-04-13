---
id: "9164546e0710"
type: "knowledge"
title: "Using the SurfaceTool"
tags:
  - scripting
  - 3d
source_type: "document"
source_file: "tutorials/3d/procedural_geometry/surfacetool.rst"
sections: "13"
code_samples: "0"
created_at: "2026-04-08T09:05:24.794134"
---

# Using the SurfaceTool

## Content Preview

.. _doc_surfacetool:

Using the SurfaceTool
=====================

The :ref:`SurfaceTool <class_surfacetool>` provides a useful interface for constructing geometry.
The interface is similar to the :ref:`ImmediateMesh <class_ImmediateMesh>` class. You
set each per-vertex attribute (e.g. normal, uv, color) and then when you add a vertex it
captures the attributes.

The SurfaceTool also provides some useful helper functions like ``index()`` and ``generate_normals()``.

Attributes are added before e


## Connections

- [[GD0101_ The exported member is static]] (incoming)
- [[GD0106_ The exported property is an explicit interface implementation]] (incoming)
- [[Viewport and canvas transforms]] (incoming)
- [[Rendering]] (incoming)
- [[GD0110_ The exported tool button is not a Callable]] (outgoing)
- [[What is GDExtension_]] (outgoing)
- [[GD0402_ The class must not be generic]] (outgoing)
- [[The .gdextension file]] (outgoing)
- [[Using CharacterBody2D_3D]] (incoming)
- [[Main build system_ Working with SCons]] (incoming)
- [[3D text]] (incoming)
- [[Introduction to global illumination]] (incoming)
- [[Rendering]] (outgoing)
- [[2D antialiasing]] (outgoing)
- [[Third-person camera with spring arm]] (outgoing)
- [[Physics introduction]] (outgoing)