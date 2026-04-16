---
id: "a23501eefd07"
type: "knowledge"
title: "C# exported properties"
tags:
  - scripting
  - example
  - ui
  - 3d
source_type: "document"
source_file: "tutorials/scripting/c_sharp/c_sharp_exports.rst"
sections: "45"
code_samples: "3"
created_at: "2026-04-08T09:05:24.756856"
---

# C# exported properties

## Content Preview

.. _doc_c_sharp_exports:

C# exported properties
======================

In Godot, class members can be exported. This means their value gets saved along
with the resource (such as the :ref:`scene <class_PackedScene>`) they're
attached to. They will also be available for editing in the property editor.
Exporting is done by using the ``[Export]`` attribute.

.. code-block:: csharp

    using Godot;

    public partial class ExportExample : Node3D
    {
        [Export]
        public int Number {


## Connections

- [[GD0109_ The '[ExportToolButton]' attribute cannot be used with another '[Export]' attribute]] (incoming)
- [[Secondary build system_ Working with CMake]] (incoming)
- [[C#_.NET]] (incoming)
- [[Pausing games and process mode]] (incoming)
- [[3D rendering limitations]] (outgoing)
- [[Output panel]] (outgoing)
- [[GD0301_ The generic type argument must be a Variant compatible type]] (outgoing)
- [[Process material properties]] (outgoing)
- [[GD0302_ The generic type parameter must be annotated with the '[MustBeVariant]' attribute]] (incoming)
- [[Pausing games and process mode]] (incoming)
- [[Using SceneTree]] (incoming)
- [[GD0107_ Types not derived from Node should not export Node members]] (incoming)
- [[GD0002_ Missing partial modifier on declaration of type which contains nested classes that derive from GodotObject]] (outgoing)
- [[GD0003_ Found multiple classes with the same name in the same script file]] (outgoing)
- [[GDScript warning system]] (outgoing)
- [[GD0301_ The generic type argument must be a Variant compatible type]] (outgoing)
- [[3D Particle collisions]] (incoming)
- [[Pausing games and process mode]] (incoming)
- [[3D antialiasing]] (incoming)
- [[3D Particle attractors]] (incoming)
- [[3D rendering limitations]] (outgoing)
- [[Creating a 3D particle system]] (outgoing)
- [[Using Voxel global illumination]] (outgoing)
- [[Large world coordinates]] (outgoing)
- [[GDScript reference]] (incoming)
- [[Occlusion culling]] (incoming)
- [[Secondary build system_ Working with CMake]] (incoming)
- [[3D antialiasing]] (incoming)
- [[GDScript warning system]] (outgoing)
- [[GD0301_ The generic type argument must be a Variant compatible type]] (outgoing)
- [[Custom drawing in 2D]] (outgoing)
- [[File system]] (outgoing)