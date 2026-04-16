---
id: "aeb194914a2a"
type: "knowledge"
title: "The C interface JSON file"
tags: []
source_type: "document"
source_file: "tutorials/scripting/gdextension/gdextension_interface_json_file.rst"
sections: "21"
code_samples: "2"
created_at: "2026-04-08T09:05:24.734480"
---

# The C interface JSON file

## Content Preview

.. _doc_gdextension_interface_json_file:

The C interface JSON file
=========================

The ``gdextension_interface.json`` file is the "source of truth" for the C API that
Godot uses to communicate with GDExtensions.

You can use the Godot executable to dump the file by using the following command:

.. code-block:: shell

    godot --headless --dump-gdextension-interface-json

This file is intended to be used by GDExtension language bindings to generate code for
using this API in whatever


## Connections

- No connections