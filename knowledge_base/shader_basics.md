---
source: expander
generated: 2026-04-22T17:29:13.110949
category: godot_advanced
mode: coding
---

# Godot Shader Language (GDShader)

## Shader Types
- **Spatial**: 3D lighting, materials
- **CanvasItem**: 2D sprites, UI effects
- **Particles**: GPU particle behavior

## Basic Spatial Shader
```glsl
shader_type spatial;

uniform vec4 albedo : source_color;
uniform float metallic;
uniform float roughness;

void vertex() {
    UV = UV * 2.0; // Tile texture
}

void fragment() {
    ALBEDO = albedo.rgb;
    METALLIC = metallic;
    ROUGHNESS = roughness;
}
```

## Common Effects

### Dissolve Effect
```glsl
uniform sampler2D noise_texture;
uniform float dissolve_amount : hint_range(0, 1);

void fragment() {
    float noise = texture(noise_texture, UV).r;
    if (noise < dissolve_amount) discard;
    ALBEDO = mix(albedo, vec3(1.0), 
                 smoothstep(dissolve_amount-0.1, dissolve_amount, noise));
}
```

### Fresnel Outline
```glsl
uniform vec4 outline_color : source_color;

void fragment() {
    float fresnel = dot(NORMAL, VIEW);
    float outline = smoothstep(0.2, 0.0, fresnel);
    ALBEDO = mix(albedo, outline_color.rgb, outline);
}
```

## Performance Tips
- Use precision hints: `lowp`, `mediump`, `highp`
- Avoid branching; use `mix()` or `step()`
- Minimize texture samples
- Use `INSTANCE_CUSTOM` for batching
