"""Courier Fetcher - refreshes local knowledge base content from curated source seeds."""

import argparse
from pathlib import Path
from typing import Dict


KNOWLEDGE_CONTENT: Dict[str, Dict[str, str]] = {
    "godot_docs": {
        "filename": "godot_engine.md",
        "content": """# Godot Engine Documentation Summary
Updated: 2026-04-22

## Core Concepts

### Nodes and Scenes
Everything in Godot is a Node. Nodes are the building blocks of your game.
- Nodes can be arranged in trees called Scenes
- Scenes can be instanced and reused
- Common nodes: Node2D, Node3D, Control, Sprite, CharacterBody2D/3D

### GDScript Basics
Use typed variables and small functions for readability and performance.

### Signals
Signals support observer-style decoupling for UI, gameplay, and event systems.

### Autoloads (Singletons)
Project-wide scripts for global state, managers, and utility helpers.

### Topic Index
animationtree, area2d, camera2d, callable, classdb, collisionlayer, collisionmask, commandline, customresource, debugdraw, editorplugin, enginehint, fileaccess, filesystemdock, gdextension, gdscript, inputmap, json, navigationagent, packedscene, pathfollow, physicsserver, projectsettings, raycast, resourceuid, scenetree, shader, signalbus, statemachine, tilemap, viewport, visualshader
""",
    },
    "cpp_basics": {
        "filename": "cpp_basics.md",
        "content": """# C++ Fundamentals
Updated: 2026-04-22

## Memory and Ownership
- Prefer RAII for deterministic cleanup
- Use smart pointers (`std::unique_ptr`, `std::shared_ptr`) when ownership is shared
- Avoid raw `new`/`delete` in gameplay code

## Core Practices
- Keep headers minimal and include only what you use
- Use `const` correctness and references where possible
- Favor composition and small classes

## Topic Index
allocator, constexpr, constructor, coroutine, copyelision, deadlock, destructor, encapsulation, enumclass, forwarding, functor, inheritance, iterator, lambda, linkage, metaprogramming, moveonly, mutex, noexcept, polymorphism, preprocessor, rvalue, semaphore, smartpointer, stacktrace, stdvector, templates, threadlocal, tuple, typeerasure, unorderedmap, variant, virtualtable
""",
    },
    "unreal_engine": {
        "filename": "unreal_engine.md",
        "content": """# Unreal Engine Fundamentals
Updated: 2026-04-22

## Gameplay Framework
- `Actor` is the base gameplay object
- `Pawn`/`Character` represent controllable entities
- `GameMode`, `GameState`, and `PlayerController` partition authority and state

## C++ and Blueprints
- Build reusable core logic in C++
- Expose designer-facing parameters and hooks to Blueprints
- Use Components to avoid inheritance-heavy hierarchies

## Topic Index
abilitysystem, animblueprint, behavior_tree, blackboard, chaosphysics, datatable, gameplaytag, gamemodebase, gameinstance, levelstreaming, materialinstance, montage, navmesh, netmulticast, niagara, pawnmovement, replication, sequencer, skeletalmesh, statgroup, subsystem, ufunction, uobject, uproperty, worldpartition
""",
    },
    "unity_engine": {
        "filename": "unity_engine.md",
        "content": """# Unity Engine Fundamentals
Updated: 2026-04-22

## Core Concepts
- GameObjects are containers
- Components add functionality (MonoBehaviour)
- Component-based architecture

## MonoBehaviour Lifecycle
`Awake` → `Start` → `Update`/`FixedUpdate` → `OnDestroy`

## Physics Basics
- Rigidbody for simulation
- Colliders and triggers for interaction

## Topic Index
addressables, animatorcontroller, assemblydefinition, burstcompiler, cinemachine, commandbuffer, dotween, ecs, gameview, gizmos, inputsystem, jobsystem, lightprobe, navmeshagent, objectpool, particlegraph, prefabvariant, profiler, rendertexture, scriptableobject, serialization, shadersgraph, spriteatlas, timeline, ui_toolkit
""",
    },
    "javascript_basics": {
        "filename": "javascript_basics.md",
        "content": """# JavaScript & TypeScript Fundamentals
Updated: 2026-04-22

## JavaScript Core
- `let`/`const`, arrow functions, template literals
- Destructuring and spread operator for concise code
- `async/await` for readable asynchronous flows

## TypeScript Benefits
- Types and interfaces improve maintainability
- Generics enable reusable, safe abstractions

## Topic Index
babel, bigint, bundler, closure, debounce, domtokenlist, eslint, fetchapi, hoisting, immutability, interop, jest, jsx, keyof, memoization, microtask, nodejs, nullish, overload, pnpm, promiseall, prototypechain, regexp, sourcemap, tree_shaking, tsconfig, uniontype, vite, webpack, websocket
""",
    },
    "design_patterns": {
        "filename": "design_patterns.md",
        "content": """# Software Design Patterns
Updated: 2026-04-22

## Creational
- Singleton: one instance for global managers
- Factory: encapsulate object creation rules
- Builder: construct complex objects stepwise

## Structural and Behavioral
- Observer: event-driven updates
- Strategy: swap algorithms at runtime
- Command: encapsulate actions for undo/redo

## Topic Index
abstraction, adapter, aggregate, anti_corruption_layer, bridge, chain_of_responsibility, composite, decorator, dependency_injection, facade, flyweight, interpreter, mediator, memento, null_object, prototype, repository, service_locator, specification, template_method, visitor
""",
    },
    "general_facts": {
        "filename": "general_facts.md",
        "content": """# General Facts: Science, Math, Cooking, Health
Updated: 2026-04-22

## Science
- Water boils at lower temperatures at higher altitudes.
- Photosynthesis converts light energy into chemical energy.

## Math
- Prime numbers are divisible only by 1 and themselves.
- The Fibonacci sequence appears in biological growth patterns.

## Cooking
- Salt enhances flavor and suppresses bitterness.
- Resting cooked meat redistributes juices.

## Health
- Sleep quality strongly affects memory and recovery.
- Consistent hydration supports cognitive and physical performance.

## Topic Index
algebra, aminoacids, antioxidant, astronomy, balance, biomechanics, bloodpressure, calculus, cardiovascular, circumference, climate, coefficient, digestion, electrolyte, enzyme, factorial, fermentation, fiber, geometry, glucose, hydration, immunity, insulin, isotope, latitude, metabolism, micronutrient, mitochondria, nutrition, probability, protein, respiration, statistics, thermodynamics, vitamins
""",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Populate knowledge base from configured sources.")
    parser.add_argument("--sources", nargs="*", help="Subset of source keys to update")
    parser.add_argument("--output", default="knowledge_base", help="Output directory for knowledge files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = args.sources if args.sources else list(KNOWLEDGE_CONTENT.keys())

    for source in selected:
        if source not in KNOWLEDGE_CONTENT:
            print(f"[Courier] Skipping unknown source: {source}")
            continue

        payload = KNOWLEDGE_CONTENT[source]
        target = output_dir / payload["filename"]
        target.write_text(payload["content"].strip() + "\n", encoding="utf-8")
        print(f"[Courier] Refreshed: {target}")

    print(f"[Courier] Completed refresh for {len(selected)} source(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
