"""
Ether — Godot AI Development Assistant
SMGA 3.0 — Full UI overhaul: sidebar brain graph + scrollable chat + mode selector
Run: streamlit run app.py
"""

import json
import time
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

from core import (
    EtherSession,
    classify,
    is_casual,
    recall,
    remember,
    build_project_map,
    extract_zip,
    select_context,
    run_pipeline,
    preview_changes,
    apply_changes,
)

# ── Config ─────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Ether",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;500&display=swap');

:root {
    --bg:        #07070a;
    --surface:   #0e0e14;
    --surface2:  #13131b;
    --border:    #1c1c28;
    --border2:   #2a2a3a;
    --accent:    #6e6af0;
    --accent2:   #9d8ff0;
    --accentglow:#6e6af055;
    --text:      #c4c4d4;
    --muted:     #4a4a64;
    --success:   #3ddc84;
    --warn:      #f5c842;
    --danger:    #f06e6e;
    --gold:      #f5c842;
    --mono:      'Space Mono', monospace;
    --sans:      'Inter', sans-serif;
    --radius:    6px;
}

html, body, [class*="css"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--sans) !important;
}

.stApp { background: var(--bg) !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
    min-width: 340px !important;
    max-width: 380px !important;
}
[data-testid="stSidebar"] > div { padding: 0 !important; }

/* ── Input ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--surface2) !important;
    border: 1px solid var(--border2) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 0.82rem !important;
    border-radius: var(--radius) !important;
    transition: border-color 0.2s !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accentglow) !important;
    outline: none !important;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--surface2) !important;
    border: 1px solid var(--border2) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.06em !important;
    border-radius: var(--radius) !important;
    transition: all 0.18s !important;
    padding: 0.4rem 0.9rem !important;
}
.stButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent2) !important;
    background: #1a1a2a !important;
}
.stButton > button[kind="primary"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: #fff !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--accent2) !important;
    border-color: var(--accent2) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    font-family: var(--mono) !important;
    font-size: 0.74rem !important;
    letter-spacing: 0.08em !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.45rem 1.1rem !important;
    transition: color 0.15s !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent2) !important;
    border-bottom-color: var(--accent) !important;
}

/* ── Code ── */
code, pre {
    font-family: var(--mono) !important;
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text) !important;
    font-size: 0.78rem !important;
}

/* ── Chat container ── */
.chat-scroll-container {
    height: calc(100vh - 260px);
    min-height: 300px;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 0.5rem 0.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    scrollbar-width: thin;
    scrollbar-color: var(--border2) transparent;
}
.chat-scroll-container::-webkit-scrollbar { width: 4px; }
.chat-scroll-container::-webkit-scrollbar-track { background: transparent; }
.chat-scroll-container::-webkit-scrollbar-thumb {
    background: var(--border2);
    border-radius: 2px;
}

/* ── Chat bubbles ── */
.msg-user {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: var(--radius);
    padding: 0.65rem 0.9rem;
    font-size: 0.85rem;
    word-wrap: break-word;
    overflow-wrap: break-word;
    white-space: pre-wrap;
    animation: msgIn 0.2s ease-out;
    max-width: 100%;
}
.msg-ai {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--success);
    border-radius: var(--radius);
    padding: 0.65rem 0.9rem;
    font-size: 0.85rem;
    word-wrap: break-word;
    overflow-wrap: break-word;
    white-space: pre-wrap;
    animation: msgIn 0.2s ease-out;
    max-width: 100%;
}
.msg-label {
    font-family: var(--mono);
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    margin-bottom: 0.3rem;
    opacity: 0.5;
}
.msg-user .msg-label { color: var(--accent2); }
.msg-ai .msg-label { color: var(--success); }

@keyframes msgIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Thinking animation ── */
.thinking-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: var(--radius);
    font-family: var(--mono);
    font-size: 0.75rem;
    color: var(--accent2);
    animation: msgIn 0.2s ease-out;
}
.thinking-dots {
    display: flex;
    gap: 3px;
}
.thinking-dots span {
    width: 5px; height: 5px;
    background: var(--accent);
    border-radius: 50%;
    animation: dot-pulse 1.2s ease-in-out infinite;
}
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dot-pulse {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.3; }
    40%            { transform: scale(1.0); opacity: 1.0; }
}

/* ── Mode selector ── */
.mode-selector {
    display: flex;
    gap: 4px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 3px;
    width: fit-content;
}
.mode-btn {
    padding: 3px 10px;
    border-radius: 4px;
    font-family: var(--mono);
    font-size: 0.68rem;
    letter-spacing: 0.07em;
    cursor: pointer;
    border: none;
    background: transparent;
    color: var(--muted);
    transition: all 0.15s;
}
.mode-btn.active {
    background: var(--accent);
    color: #fff;
}
.mode-btn:hover:not(.active) { color: var(--text); background: var(--border); }

/* ── Input row ── */
.input-row {
    display: flex;
    gap: 6px;
    align-items: flex-end;
    padding: 0.5rem 0;
}

/* ── Badges ── */
.badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 3px;
    font-family: var(--mono);
    font-size: 0.65rem;
    letter-spacing: 0.08em;
}
.badge-ok   { background: rgba(61,220,132,0.1);  color: var(--success); border: 1px solid rgba(61,220,132,0.25); }
.badge-warn { background: rgba(245,200,66,0.1);  color: var(--warn);    border: 1px solid rgba(245,200,66,0.25); }
.badge-err  { background: rgba(240,110,110,0.1); color: var(--danger);  border: 1px solid rgba(240,110,110,0.25); }
.badge-info { background: rgba(110,106,240,0.1); color: var(--accent2); border: 1px solid rgba(110,106,240,0.25); }

/* ── Diff ── */
.diff-add { color: var(--success); font-family: var(--mono); font-size: 0.75rem; }
.diff-rem { color: var(--danger);  font-family: var(--mono); font-size: 0.75rem; }
.diff-ctx { color: var(--muted);   font-family: var(--mono); font-size: 0.75rem; }

/* ── Metrics ── */
.stMetric label { color: var(--muted) !important; font-size: 0.68rem !important; font-family: var(--mono) !important; }

/* ── Misc ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
hr { border-color: var(--border) !important; }
.stSelectbox > div > div {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
}
.streamlit-expanderHeader {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    font-family: var(--mono) !important;
    font-size: 0.78rem !important;
    color: var(--muted) !important;
    border-radius: var(--radius) !important;
}

/* ── Scrollbar global ── */
* { scrollbar-width: thin; scrollbar-color: var(--border2) transparent; }
*::-webkit-scrollbar { width: 4px; height: 4px; }
*::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

/* ── Sidebar header ── */
.sidebar-header {
    padding: 1.2rem 1.2rem 0.6rem;
    border-bottom: 1px solid var(--border);
}
.sidebar-section {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border);
}
.sidebar-title {
    font-family: var(--mono);
    font-size: 0.65rem;
    letter-spacing: 0.15em;
    color: var(--muted);
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)


# ── Session Init ───────────────────────────────────────────────────────────────

def _session() -> EtherSession:
    if "ether" not in st.session_state:
        st.session_state["ether"] = EtherSession()
    return st.session_state["ether"]


def _pending() -> list:
    if "pending_changes" not in st.session_state:
        st.session_state["pending_changes"] = []
    return st.session_state["pending_changes"]


def _get_api_key() -> str:
    if "api_key" in st.session_state and st.session_state["api_key"]:
        return st.session_state["api_key"]
    if "sidebar_api_key" in st.session_state and st.session_state["sidebar_api_key"]:
        return st.session_state["sidebar_api_key"]
    try:
        if "OPENROUTER_API_KEY" in st.secrets:
            return st.secrets["OPENROUTER_API_KEY"]
    except Exception:
        pass
    import os
    env_key = os.getenv("OPENROUTER_API_KEY")
    if env_key:
        return env_key
    raise RuntimeError("API key not found.")


def _get_uploaded_file_key(uploaded) -> str:
    return f"{uploaded.name}:{uploaded.size}"


def _handle_upload(uploaded, s: EtherSession):
    data = uploaded.read()
    if not data:
        st.error("Empty ZIP.")
        return False
    ok, msg, file_contents = extract_zip(data)
    if not ok:
        st.error(msg)
        return False
    pm = build_project_map(file_contents)
    s.project_loaded = True
    s.project_files = list(file_contents.keys())
    s.file_contents = file_contents
    s.project_map = pm
    s.active_file = None
    st.success(f"✓ {msg}")
    scripts = pm["stats"]["script_count"]
    scenes = pm["stats"]["scene_count"]
    issues = pm["stats"].get("total_issues", 0)
    improvements = pm["stats"].get("total_improvements", 0)
    s.add_turn("assistant", (
        f"Project loaded: {scripts} scripts, {scenes} scenes. "
        f"Found {issues} potential issues and {improvements} improvement opportunities. "
        f"Brain map updated — check the sidebar."
    ))
    return True


# ── Brain Graph (Three.js) ─────────────────────────────────────────────────────

def _build_graph_data(s: EtherSession) -> dict:
    """
    Convert project map into nodes/edges for the brain graph.
    
    Returns a dict with:
    - nodes: list of node objects with id, label, type, status, tooltip
    - links: list of edge objects with source, target
    
    Status values: "error", "improve", "clean", "scene"
    Type values: "script", "scene"
    """
    if not s.project_loaded or not s.project_map:
        return {"nodes": [], "edges": []}

    pm = s.project_map
    nodes = []
    links = []
    node_ids = {}

    # Script nodes
    for i, (path, data) in enumerate(pm.get("scripts", {}).items()):
        nid = f"s{i}"
        node_ids[path] = nid
        issues = data.get("issues", [])
        improvements = data.get("improvements", [])
        name = Path(path).stem

        if issues:
            status = "error"
            tooltip = f"📄 {name}\n\n⚠️ ISSUES:\n" + "\n".join(f"• {x}" for x in issues[:5])
        elif improvements:
            status = "improve"
            tooltip = f"📄 {name}\n\n💡 IMPROVEMENTS:\n" + "\n".join(f"• {x}" for x in improvements[:5])
        else:
            status = "clean"
            tooltip = f"📄 {name}\n\nExtends: {data.get('extends', 'None')}\nFunctions: {len(data.get('functions', []))}"

        nodes.append({
            "id": nid,
            "label": name,
            "status": status,
            "tooltip": tooltip,
            "type": "script",
        })

    # Scene nodes
    for i, (path, data) in enumerate(pm.get("scenes", {}).items()):
        nid = f"sc{i}"
        node_ids[path] = nid
        name = Path(path).stem
        nodes.append({
            "id": nid,
            "label": name,
            "status": "scene",
            "tooltip": f"🎬 Scene: {name}\n\nNodes: {len(data.get('nodes', []))}",
            "type": "scene",
        })
        # Link: scene → script
        for script_path in data.get("scripts", []):
            if script_path in node_ids:
                links.append({"source": nid, "target": node_ids[script_path]})

    # Script extends relationships
    for path, data in pm.get("scripts", {}).items():
        ext = data.get("extends", "")
        if ext:
            for other_path, other_data in pm.get("scripts", {}).items():
                if Path(other_path).stem == ext and path != other_path:
                    if path in node_ids and other_path in node_ids:
                        links.append({
                            "source": node_ids[path],
                            "target": node_ids[other_path],
                        })

    return {"nodes": nodes, "edges": links}


def _render_brain_graph(graph_data: dict, height: int = 480):
    """
    Render Three.js interactive force-directed brain graph.
    
    Features:
    - Force-directed layout with physics simulation (repulsion + spring links + center gravity)
    - Pan/zoom controls (drag to pan, scroll to zoom)
    - Draggable nodes (grab and move individual nodes)
    - Hover highlighting with tooltips
    - Color-coded nodes by status (error=red, improve=yellow, clean=blue, scene=gray)
    - Dark theme matching Streamlit dark mode
    
    Force Simulation Parameters (tunable):
    - REPEL_STRENGTH: How strongly nodes push apart (higher = more spread out)
    - LINK_DISTANCE: Resting length of edges (higher = looser connections)
    - LINK_STRENGTH: How stiff the springs are (0-1, higher = tighter)
    - CENTER_GRAVITY: Pull toward center (prevents nodes flying to infinity)
    - DAMPING: Velocity decay per frame (lower = longer settling time)
    """
    nodes_json = json.dumps(graph_data["nodes"])
    edges_json = json.dumps(graph_data["edges"])

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ 
    background: #07070a; 
    overflow: hidden; 
    font-family: 'Space Mono', monospace;
    touch-action: none;
}}
#container {{ 
    width: 100%; 
    height: {height}px; 
    position: relative;
}}
canvas {{ display: block; width: 100%; height: {height}px; }}
#tooltip {{
    position: absolute; pointer-events: none;
    background: rgba(13,13,20,0.95);
    border: 1px solid #2a2a3a;
    border-left: 2px solid #6e6af0;
    color: #c4c4d4;
    font-family: 'Space Mono', monospace; font-size: 11px;
    padding: 8px 12px; border-radius: 4px;
    white-space: pre; max-width: 260px;
    opacity: 0; transition: opacity 0.15s;
    z-index: 999; line-height: 1.5;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}}
#legend {{
    position: absolute; bottom: 12px; left: 12px;
    display: flex; gap: 12px; align-items: center;
    font-family: 'Space Mono', monospace; font-size: 10px; color: #4a4a64;
    background: rgba(13,13,20,0.8);
    padding: 6px 10px; border-radius: 4px;
    border: 1px solid #1c1c28;
}}
.leg {{ display: flex; align-items: center; gap: 5px; }}
.leg-dot {{ width: 9px; height: 9px; border-radius: 50%; }}
#stats {{
    position: absolute; top: 12px; right: 12px;
    font-family: 'Space Mono', monospace; font-size: 10px; color: #4a4a64;
    text-align: right; line-height: 1.6;
    background: rgba(13,13,20,0.8);
    padding: 6px 10px; border-radius: 4px;
    border: 1px solid #1c1c28;
}}
#controls-hint {{
    position: absolute; top: 12px; left: 12px;
    font-family: 'Space Mono', monospace; font-size: 9px; color: #2a2a3a;
    line-height: 1.4;
    pointer-events: none;
}}
</style>
</head>
<body>
<div id="container"></div>
<div id="tooltip"></div>
<div id="legend">
    <div class="leg"><div class="leg-dot" style="background:#f06e6e;box-shadow:0 0 6px #f06e6e66"></div>error</div>
    <div class="leg"><div class="leg-dot" style="background:#f5c842;box-shadow:0 0 6px #f5c84266"></div>improve</div>
    <div class="leg"><div class="leg-dot" style="background:#4a9eff;box-shadow:0 0 6px #4a9eff66"></div>clean</div>
    <div class="leg"><div class="leg-dot" style="background:#3a4a5a;box-shadow:0 0 6px #3a4a5a66"></div>scene</div>
</div>
<div id="stats"></div>
<div id="controls-hint">Drag: pan | Scroll: zoom | Drag node: move</div>

<!-- Three.js from CDN -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>

<script>
// ── Data ─────────────────────────────────────────────────────────────────────
const NODES = {nodes_json};
const LINKS = {edges_json};

// ── Force Simulation Parameters (TUNABLE) ────────────────────────────────────
const CONFIG = {{
    REPEL_STRENGTH: 800,        // Node repulsion force (higher = more spread)
    LINK_DISTANCE: 120,         // Resting edge length in pixels
    LINK_STRENGTH: 0.08,        // Spring stiffness (0-1, lower = looser)
    CENTER_GRAVITY: 0.02,       // Pull toward center (prevents flying away)
    DAMPING: 0.88,              // Velocity decay per frame (lower = faster stop)
    MAX_VELOCITY: 15,           // Cap node speed
    NODE_RADIUS: 12,            // Base node size
    SCENE_SIZE: 16,             // Scene node size (larger)
    CHARGE_MIN: 200,            // Minimum charge magnitude
    CHARGE_MAX: 600,            // Maximum charge magnitude
}};

// ── Three.js Setup ───────────────────────────────────────────────────────────
const container = document.getElementById('container');
const tooltip = document.getElementById('tooltip');
const statsEl = document.getElementById('stats');

let width = container.clientWidth;
let height = {height};

// Scene, Camera, Renderer
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x07070a);

// Orthographic camera for 2D-like view (easier interaction)
const frustumSize = Math.max(width, height) * 0.8;
const aspect = width / height;
const camera = new THREE.OrthographicCamera(
    -frustumSize * aspect / 2, frustumSize * aspect / 2,
    frustumSize / 2, -frustumSize / 2,
    0.1, 1000
);
camera.position.z = 100;

const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: false }});
renderer.setSize(width, height);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
container.appendChild(renderer.domElement);

// ── View Transform (Pan/Zoom) ────────────────────────────────────────────────
let viewOffset = {{ x: 0, y: 0 }};
let viewZoom = 1;
let isPanning = false;
let panStart = {{ x: 0, y: 0 }};

function updateCamera() {{
    const fs = frustumSize / viewZoom;
    const a = width / height;
    camera.left = -fs * a / 2 + viewOffset.x;
    camera.right = fs * a / 2 + viewOffset.x;
    camera.top = fs / 2 - viewOffset.y;
    camera.bottom = -fs / 2 - viewOffset.y;
    camera.updateProjectionMatrix();
}}
updateCamera();

// ── Node & Edge Objects ──────────────────────────────────────────────────────
const nodeMeshes = new Map();  // id -> mesh
const edgeLines = [];          // array of Line objects
const nodeData = new Map();    // id -> physics data

// Initialize physics data for each node
NODES.forEach(n => {{
    nodeData.set(n.id, {{
        x: (Math.random() - 0.5) * 200,
        y: (Math.random() - 0.5) * 200,
        vx: 0, vy: 0,
        fx: 0, fy: 0,  // accumulated forces
        isDragging: false,
        charge: -CONFIG.CHARGE_MAX - (Math.random() * (CONFIG.CHARGE_MIN - CONFIG.CHARGE_MAX)),
    }});
}});

// Create node geometries
function createNodeGeometry(node) {{
    const isScene = node.type === 'scene';
    const radius = isScene ? CONFIG.SCENE_SIZE : CONFIG.NODE_RADIUS;
    
    if (isScene) {{
        // Octahedron for scenes (diamond-like)
        return new THREE.OctahedronGeometry(radius * 0.7, 0);
    }} else {{
        // Sphere for scripts
        return new THREE.SphereGeometry(radius, 16, 16);
    }}
}}

// Create materials based on status
function getNodeMaterial(node, isHovered = false) {{
    const colors = {{
        error: 0xf06e6e,
        improve: 0xf5c842,
        ok: 0x4a9eff,
        scene: 0x3a4a5a,
    }};
    const glowColors = {{
        error: 0xff8888,
        improve: 0xffdd88,
        ok: 0x88ccff,
        scene: 0x6688aa,
    }};
    
    const baseColor = colors[node.status] || 0x4a4a64;
    const glowColor = glowColors[node.status] || 0x666688;
    
    return new THREE.MeshStandardMaterial({{
        color: baseColor,
        emissive: isHovered ? glowColor : baseColor,
        emissiveIntensity: isHovered ? 0.6 : 0.2,
        roughness: 0.4,
        metalness: 0.6,
    }});
}}

// Create nodes
NODES.forEach(node => {{
    const geometry = createNodeGeometry(node);
    const material = getNodeMaterial(node);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.userData = {{ nodeId: node.id, node: node }};
    mesh.position.set(nodeData.get(node.id).x, nodeData.get(node.id).y, 0);
    scene.add(mesh);
    nodeMeshes.set(node.id, mesh);
}});

// Create edges (thin lines)
const edgeMaterial = new THREE.LineBasicMaterial({{ 
    color: 0x2a2a3a, 
    transparent: true, 
    opacity: 0.4,
}});

LINKS.forEach(link => {{
    const points = [new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, 0)];
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const line = new THREE.Line(geometry, edgeMaterial);
    scene.add(line);
    edgeLines.push({{ line, link }});
}});

// ── Background Grid ──────────────────────────────────────────────────────────
const gridHelper = new THREE.GridHelper(1000, 50, 0x1a1a28, 0x1a1a28);
gridHelper.rotation.x = Math.PI / 2;
gridHelper.position.z = -1;
scene.add(gridHelper);

// ── Force-Directed Layout ────────────────────────────────────────────────────
function computeForces() {{
    // Reset forces
    nodeData.forEach(d => {{ d.fx = 0; d.fy = 0; }});
    
    // Repulsion between all pairs (Coulomb-like)
    const nodes = Array.from(nodeData.entries());
    for (let i = 0; i < nodes.length; i++) {{
        for (let j = i + 1; j < nodes.length; j++) {{
            const [id1, d1] = nodes[i];
            const [id2, d2] = nodes[j];
            
            let dx = d2.x - d1.x;
            let dy = d2.y - d1.y;
            let distSq = dx * dx + dy * dy;
            distSq = Math.max(distSq, 100); // Prevent division by zero
            
            const force = CONFIG.REPEL_STRENGTH / distSq;
            const dist = Math.sqrt(distSq);
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            
            d1.fx -= fx;
            d1.fy -= fy;
            d2.fx += fx;
            d2.fy += fy;
        }}
    }}
    
    // Spring forces for edges (Hooke's law)
    LINKS.forEach(link => {{
        const d1 = nodeData.get(link.source);
        const d2 = nodeData.get(link.target);
        if (!d1 || !d2) return;
        
        let dx = d2.x - d1.x;
        let dy = d2.y - d1.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        
        // Force proportional to displacement from rest length
        const displacement = dist - CONFIG.LINK_DISTANCE;
        const force = CONFIG.LINK_STRENGTH * displacement;
        
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        
        d1.fx += fx;
        d1.fy += fy;
        d2.fx -= fx;
        d2.fy -= fy;
    }});
    
    // Center gravity (pull everything toward origin)
    nodeData.forEach(d => {{
        d.fx -= d.x * CONFIG.CENTER_GRAVITY;
        d.fy -= d.y * CONFIG.CENTER_GRAVITY;
    }});
}}

function integrate() {{
    nodeData.forEach((d, id) => {{
        if (d.isDragging) return;  // Don't update dragged nodes
        
        // Apply forces to velocity
        d.vx += d.fx;
        d.vy += d.fy;
        
        // Damping
        d.vx *= CONFIG.DAMPING;
        d.vy *= CONFIG.DAMPING;
        
        // Velocity cap
        const v = Math.sqrt(d.vx * d.vx + d.vy * d.vy);
        if (v > CONFIG.MAX_VELOCITY) {{
            d.vx = (d.vx / v) * CONFIG.MAX_VELOCITY;
            d.vy = (d.vy / v) * CONFIG.MAX_VELOCITY;
        }}
        
        // Update position
        d.x += d.vx;
        d.y += d.vy;
    }});
}}

function updateNodePositions() {{
    nodeData.forEach((d, id) => {{
        const mesh = nodeMeshes.get(id);
        if (mesh) {{
            mesh.position.x = d.x;
            mesh.position.y = d.y;
        }}
    }});
    
    // Update edge lines
    if (edgeLines.length > 0) {{
        edgeLines.forEach((item) => {{
            const line = item.line;
            const link = item.link;
            const d1 = nodeData.get(link.source);
            const d2 = nodeData.get(link.target);
            if (d1 && d2) {{
                const positions = line.geometry.attributes.position.array;
                positions[0] = d1.x; positions[1] = d1.y; positions[2] = 0.1;
                positions[3] = d2.x; positions[4] = d2.y; positions[5] = 0.1;
                line.geometry.attributes.position.needsUpdate = true;
            }}
        }});
    }}
}}

// ── Interaction: Raycaster for Hover/Drag ────────────────────────────────────
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
let hoveredNode = null;
let draggedNode = null;
let dragPlane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
let dragOffset = new THREE.Vector3();

function getMouseNDC(clientX, clientY) {{
    const rect = renderer.domElement.getBoundingClientRect();
    return {{
        x: ((clientX - rect.left) / rect.width) * 2 - 1,
        y: -((clientY - rect.top) / rect.height) * 2 + 1,
    }};
}}

function screenToWorld(clientX, clientY) {{
    const ndc = getMouseNDC(clientX, clientY);
    const vec = new THREE.Vector3(ndc.x, ndc.y, 0.5);
    vec.unproject(camera);
    
    const dir = vec.clone().sub(camera.position).normalize();
    const distance = -camera.position.z / dir.z;
    const pos = camera.position.clone().add(dir.multiplyScalar(distance));
    return pos;
}}

renderer.domElement.addEventListener('mousemove', (e) => {{
    const ndc = getMouseNDC(e.clientX, e.clientY);
    mouse.set(ndc.x, ndc.y, 0.5);
    
    raycaster.setFromCamera(mouse, camera);
    const meshes = Array.from(nodeMeshes.values());
    const intersects = raycaster.intersectObjects(meshes);
    
    if (intersects.length > 0) {{
        const hit = intersects[0].object;
        const nodeId = hit.userData.nodeId;
        const node = hit.userData.node;
        
        if (hoveredNode !== nodeId) {{
            hoveredNode = nodeId;
            renderer.domElement.style.cursor = draggedNode ? 'grabbing' : 'pointer';
            
            // Update hover state
            nodeMeshes.forEach((mesh, id) => {{
                const n = NODES.find(x => x.id === id);
                mesh.material = getNodeMaterial(n, id === nodeId);
            }});
            
            // Show tooltip
            tooltip.style.left = (e.clientX + 16) + 'px';
            tooltip.style.top = (e.clientY + 16) + 'px';
            tooltip.textContent = node.tooltip;
            tooltip.style.opacity = '1';
        }}
        
        if (draggedNode) {{
            const worldPos = screenToWorld(e.clientX, e.clientY);
            const data = nodeData.get(draggedNode);
            data.x = worldPos.x - dragOffset.x;
            data.y = worldPos.y - dragOffset.y;
            data.vx = 0; data.vy = 0;  // Stop momentum while dragging
            updateNodePositions();
        }}
    }} else {{
        if (hoveredNode && !draggedNode) {{
            hoveredNode = null;
            renderer.domElement.style.cursor = isPanning ? 'grabbing' : 'default';
            
            nodeMeshes.forEach((mesh, id) => {{
                const n = NODES.find(x => x.id === id);
                mesh.material = getNodeMaterial(n, false);
            }});
            
            tooltip.style.opacity = '0';
        }}
    }}
    
    draw();
}});

renderer.domElement.addEventListener('mousedown', (e) => {{
    if (e.button === 0) {{  // Left click
        if (hoveredNode) {{
            draggedNode = hoveredNode;
            renderer.domElement.style.cursor = 'grabbing';
            
            const worldPos = screenToWorld(e.clientX, e.clientY);
            const data = nodeData.get(draggedNode);
            dragOffset.set(worldPos.x - data.x, worldPos.y - data.y, 0);
        }} else {{
            isPanning = true;
            panStart = {{ x: e.clientX, y: e.clientY }};
            renderer.domElement.style.cursor = 'grab';
        }}
    }}
}});

window.addEventListener('mouseup', () => {{
    if (draggedNode) {{
        // Release with a small "throw" velocity
        const data = nodeData.get(draggedNode);
        data.isDragging = false;
    }}
    draggedNode = null;
    isPanning = false;
    renderer.domElement.style.cursor = hoveredNode ? 'pointer' : 'default';
}});

renderer.domElement.addEventListener('mouseleave', () => {{
    hoveredNode = null;
    draggedNode = null;
    isPanning = false;
    tooltip.style.opacity = '0';
    renderer.domElement.style.cursor = 'default';
    nodeMeshes.forEach((mesh, id) => {{
        const n = NODES.find(x => x.id === id);
        mesh.material = getNodeMaterial(n, false);
    }});
}});

// Pan handling
renderer.domElement.addEventListener('mousemove', (e) => {{
    if (isPanning && !draggedNode) {{
        const dx = e.clientX - panStart.x;
        const dy = e.clientY - panStart.y;
        const fs = frustumSize / viewZoom;
        const a = width / height;
        viewOffset.x -= dx * (fs * a / width);
        viewOffset.y += dy * (fs / height);
        panStart = {{ x: e.clientX, y: e.clientY }};
        updateCamera();
        draw();
    }}
}});

// Zoom handling
renderer.domElement.addEventListener('wheel', (e) => {{
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    viewZoom *= zoomFactor;
    viewZoom = Math.max(0.2, Math.min(5, viewZoom));
    updateCamera();
    draw();
}}, {{ passive: false }});

// Click to log (optional communication with parent)
renderer.domElement.addEventListener('click', (e) => {{
    if (hoveredNode && !draggedNode && !isPanning) {{
        const node = NODES.find(n => n.id === hoveredNode);
        console.log('[BrainMap] Clicked:', node);
        // Try to communicate with parent Streamlit app
        try {{
            window.parent.postMessage({{ type: 'brainmap_click', nodeId: hoveredNode, node: node }}, '*');
        }} catch(err) {{}}
    }}
}});

// ── Lighting ─────────────────────────────────────────────────────────────────
const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);

const pointLight = new THREE.PointLight(0x6e6af0, 0.8, 500);
pointLight.position.set(50, 50, 100);
scene.add(pointLight);

const pointLight2 = new THREE.PointLight(0xffaa88, 0.4, 500);
pointLight2.position.set(-50, -50, 80);
scene.add(pointLight2);

// ── Animation Loop ───────────────────────────────────────────────────────────
let simulationRunning = true;
const MAX_ITERATIONS = 300;  // Run physics for N frames then slow down
let frameCount = 0;

function animate() {{
    requestAnimationFrame(animate);
    
    // Run physics simulation
    if (simulationRunning && frameCount < MAX_ITERATIONS) {{
        computeForces();
        integrate();
        updateNodePositions();
        frameCount++;
    }} else if (frameCount >= MAX_ITERATIONS) {{
        // Slow down simulation after initial settling
        if (frameCount % 5 === 0) {{
            computeForces();
            integrate();
            updateNodePositions();
        }}
        frameCount++;
    }}
    
    draw();
}}

function draw() {{
    renderer.render(scene, camera);
    
    // Update stats display
    const errs = NODES.filter(n => n.status === 'error').length;
    const imps = NODES.filter(n => n.status === 'improve').length;
    const ok = NODES.filter(n => n.status === 'ok').length;
    const scenes = NODES.filter(n => n.type === 'scene').length;
    statsEl.innerHTML = `
        <strong style="color:#6e6af0">${{NODES.length}}</strong> nodes · 
        <strong style="color:#6e6af0">${{LINKS.length}}</strong> edges<br>
        <span style="color:#f06e6e">${{errs}} errors</span> · 
        <span style="color:#f5c842">${{imps}} improve</span> · 
        <span style="color:#4a9eff">${{ok}} clean</span> · 
        <span style="color:#3a4a5a">${{scenes}} scenes</span>
    `;
}}

// ── Resize Handler ───────────────────────────────────────────────────────────
function handleResize() {{
    width = container.clientWidth;
    height = container.clientHeight;
    
    const fs = frustumSize / viewZoom;
    const a = width / height;
    camera.left = -fs * a / 2 + viewOffset.x;
    camera.right = fs * a / 2 + viewOffset.x;
    camera.top = fs / 2 - viewOffset.y;
    camera.bottom = -fs / 2 - viewOffset.y;
    camera.updateProjectionMatrix();
    
    renderer.setSize(width, height);
    draw();
}}

window.addEventListener('resize', handleResize);

// ── Start ────────────────────────────────────────────────────────────────────
animate();
console.log('[BrainMap] Initialized with', NODES.length, 'nodes and', LINKS.length, 'edges');

}} // End of NODES guard
</script>
</body>
</html>
"""
    components.html(html, height=height, scrolling=False)


# ── Sidebar ────────────────────────────────────────────────────────────────────

def _sidebar():
    s = _session()

    with st.sidebar:
        # Header
        st.markdown("""
        <div class="sidebar-header">
            <div style="font-family:'Space Mono',monospace;font-size:1.1rem;font-weight:700;
                        letter-spacing:0.14em;color:#6e6af0;">◈ ETHER</div>
            <div style="font-family:'Space Mono',monospace;font-size:0.6rem;letter-spacing:0.18em;
                        color:#4a4a64;margin-top:2px;">GODOT BRAIN MAP</div>
        </div>
        """, unsafe_allow_html=True)

        # Project upload moved to Chat tab
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">Project</div>', unsafe_allow_html=True)

        if s.project_loaded:
            stats = s.project_map.get("stats", {})
            c1, c2 = st.columns(2)
            c1.metric("Scripts", stats.get("script_count", 0))
            c2.metric("Scenes", stats.get("scene_count", 0))
            c1.metric("Issues", stats.get("total_issues", 0))
            c2.metric("Improve", stats.get("total_improvements", 0))
        else:
            st.markdown(
                '<div style="color:#4a4a64;font-family:monospace;font-size:0.7rem;'
                'padding:0.5rem 0;">Upload a ZIP file from the CHAT tab to load your project.</div>',
                unsafe_allow_html=True
            )

        st.markdown('</div>', unsafe_allow_html=True)

        # API Key
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">API Key</div>', unsafe_allow_html=True)
        api_input = st.text_input("", type="password", key="sidebar_api_key",
                                   placeholder="sk-or-...", label_visibility="collapsed")
        if api_input:
            st.session_state["api_key"] = api_input
        st.markdown('</div>', unsafe_allow_html=True)

        # Brain Graph
        st.markdown('<div style="padding:0.5rem 0.75rem;">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">Brain Map</div>', unsafe_allow_html=True)

        if s.project_loaded and s.project_map:
            graph_data = _build_graph_data(s)
            if graph_data["nodes"]:
                _render_brain_graph(graph_data, height=420)
            else:
                st.markdown(
                    '<div style="color:#4a4a64;font-family:monospace;font-size:0.72rem;'
                    'padding:1rem 0;">No GDScript files found.</div>',
                    unsafe_allow_html=True
                )
        else:
            # Empty state placeholder
            st.markdown("""
            <div style="height:220px;display:flex;align-items:center;justify-content:center;
                        border:1px dashed #1c1c28;border-radius:6px;margin:0.5rem 0;">
                <div style="text-align:center;color:#2a2a3a;">
                    <div style="font-size:1.8rem;margin-bottom:0.4rem;">◈</div>
                    <div style="font-family:monospace;font-size:0.65rem;letter-spacing:0.1em;">
                        Upload ZIP to activate
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


# ── Chat Tab ───────────────────────────────────────────────────────────────────

def _tab_chat():
    s = _session()

    # API key gate
    api_key = None
    try:
        api_key = _get_api_key()
    except RuntimeError:
        st.markdown("### Enter OpenRouter API Key")
        fallback = st.text_input("API Key", type="password", key="global_api_key")
        if fallback:
            st.session_state["api_key"] = fallback
            st.rerun()
        st.stop()

    # ── Mode selector row ──
    mode_labels = {"coding": "⌨ Coding", "general": "◎ General", "mixed": "⊕ Mixed"}
    current_mode = s.chat_mode if hasattr(s, 'chat_mode') else "mixed"

    cols = st.columns([1, 1, 1, 3])
    mode_changed = False
    for i, (k, label) in enumerate(mode_labels.items()):
        with cols[i]:
            active = "primary" if current_mode == k else "secondary"
            if st.button(label, key=f"mode_{k}", type=active if current_mode == k else "secondary",
                         use_container_width=True):
                s.chat_mode = k
                mode_changed = True

    if mode_changed:
        st.rerun()

    # Pending changes banner
    pending = _pending()
    if pending:
        st.markdown(
            f'<span class="badge badge-warn">⚠ {len(pending)} pending change(s) — see Apply tab</span>',
            unsafe_allow_html=True
        )

    # ── Chat history (scrollable) ──
    chat_html_parts = []
    for turn in s.history:
        role = turn["role"]
        content = turn["content"].replace("<", "&lt;").replace(">", "&gt;")
        if role == "user":
            chat_html_parts.append(
                f'<div class="msg-user"><div class="msg-label">YOU</div>{content}</div>'
            )
        else:
            chat_html_parts.append(
                f'<div class="msg-ai"><div class="msg-label">ETHER</div>{content}</div>'
            )

    # Thinking state
    if st.session_state.get("_thinking", False):
        step = st.session_state.get("_thinking_step", "Processing...")
        chat_html_parts.append(f"""
        <div class="thinking-bar">
            <div class="thinking-dots">
                <span></span><span></span><span></span>
            </div>
            {step}
        </div>
        """)

    scroll_id = "chat_scroll_bottom"
    all_msgs = "\n".join(chat_html_parts)

    components.html(f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Space+Mono&display=swap" rel="stylesheet">
    <style>
    * {{ box-sizing: border-box; }}
    body {{ margin:0; padding:0; background:#07070a; }}
    .chat-wrap {{
        height: calc(100vh - 220px);
        min-height: 250px;
        overflow-y: auto;
        overflow-x: hidden;
        padding: 0.5rem 0.5rem 1rem;
        display: flex;
        flex-direction: column;
        gap: 6px;
        scrollbar-width: thin;
        scrollbar-color: #2a2a3a transparent;
    }}
    .chat-wrap::-webkit-scrollbar {{ width: 4px; }}
    .chat-wrap::-webkit-scrollbar-thumb {{ background: #2a2a3a; border-radius: 2px; }}
    .msg-user {{
        background: #0e0e14; border: 1px solid #1c1c28;
        border-left: 3px solid #6e6af0; border-radius: 6px;
        padding: 0.6rem 0.85rem; font-size: 0.83rem;
        word-wrap: break-word; white-space: pre-wrap;
        color: #c4c4d4; font-family: 'Space Mono', monospace;
        animation: msgIn 0.2s ease-out;
    }}
    .msg-ai {{
        background: #07070a; border: 1px solid #1c1c28;
        border-left: 3px solid #3ddc84; border-radius: 6px;
        padding: 0.6rem 0.85rem; font-size: 0.83rem;
        word-wrap: break-word; white-space: pre-wrap;
        color: #c4c4d4; font-family: 'Space Mono', monospace;
        animation: msgIn 0.2s ease-out;
    }}
    .msg-label {{
        font-size: 0.6rem; letter-spacing: 0.12em; margin-bottom: 0.25rem; opacity: 0.45;
    }}
    .msg-user .msg-label {{ color: #9d8ff0; }}
    .msg-ai .msg-label {{ color: #3ddc84; }}
    .thinking-bar {{
        display: flex; align-items: center; gap: 8px;
        padding: 0.45rem 0.75rem;
        background: #0e0e14; border: 1px solid #1c1c28;
        border-left: 3px solid #6e6af0; border-radius: 6px;
        font-family: monospace; font-size: 0.72rem; color: #9d8ff0;
    }}
    .dots {{ display:flex; gap:3px; }}
    .dots span {{
        width:5px;height:5px;background:#6e6af0;border-radius:50%;
        animation: dp 1.2s ease-in-out infinite;
    }}
    .dots span:nth-child(2){{animation-delay:.2s}}
    .dots span:nth-child(3){{animation-delay:.4s}}
    @keyframes dp {{ 0%,80%,100%{{transform:scale(0.6);opacity:0.3}} 40%{{transform:scale(1);opacity:1}} }}
    @keyframes msgIn {{ from{{opacity:0;transform:translateY(5px)}} to{{opacity:1;transform:translateY(0)}} }}
    </style>
    <div class="chat-wrap" id="cw">
    {all_msgs}
    <div id="{scroll_id}"></div>
    </div>
    <script>
    const el = document.getElementById('{scroll_id}');
    if(el) el.scrollIntoView({{behavior:'smooth'}});
    </script>
    """, height=max(300, min(600, 200 + len(s.history) * 60)), scrolling=False)

    # ── Input area ──
    st.markdown("")
    
    # Unified upload section - visible in chat tab (shows project status if already loaded)
    st.markdown(
        '<div style="background:var(--surface2);border:1px solid var(--border);'
        'border-radius:6px;padding:0.75rem 1rem;margin-bottom:0.75rem;">',
        unsafe_allow_html=True
    )
    
    if not s.project_loaded:
        # Show upload prompt when no project is loaded
        st.markdown(
            '<div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;">',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div style="font-family:var(--mono);font-size:0.75rem;color:var(--text);">'
            '📁 Upload your Godot project ZIP to begin</div>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        uploaded = st.file_uploader("", type=["zip"], key="chat_main_upload",
                                     label_visibility="collapsed")
        if uploaded is not None:
            key = _get_uploaded_file_key(uploaded)
            if st.session_state.get("last_uploaded_file_key") != key:
                success = _handle_upload(uploaded, s)
                if success:
                    st.session_state["last_uploaded_file_key"] = key
                    st.rerun()
    else:
        # Show project status when project is loaded
        stats = s.project_map.get("stats", {})
        st.markdown(
            '<div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap;">',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div style="font-family:var(--mono);font-size:0.7rem;color:var(--success);">'
            f'✓ Project loaded</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div style="font-family:var(--mono);font-size:0.65rem;color:var(--muted);">'
            f'{stats.get("script_count", 0)} scripts</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div style="font-family:var(--mono);font-size:0.65rem;color:var(--muted);">'
            f'{stats.get("scene_count", 0)} scenes</div>',
            unsafe_allow_html=True
        )
        issues = stats.get("total_issues", 0)
        improvements = stats.get("total_improvements", 0)
        if issues > 0:
            st.markdown(
                f'<div style="font-family:var(--mono);font-size:0.65rem;color:var(--danger);">'
                f'{issues} issues</div>',
                unsafe_allow_html=True
            )
        if improvements > 0:
            st.markdown(
                f'<div style="font-family:var(--mono);font-size:0.65rem;color:var(--warn);">'
                f'{improvements} improvements</div>',
                unsafe_allow_html=True
            )
        # Allow re-upload option
        st.markdown(
            '<div style="flex-grow:1;"></div>',
            unsafe_allow_html=True
        )
        reupload = st.button("🔄 New Project", key="reupload_btn", 
                            help="Upload a different project")
        if reupload:
            s.project_loaded = False
            s.project_files = []
            s.file_contents = {}
            s.project_map = {}
            s.active_file = None
            st.session_state.pop("last_uploaded_file_key", None)
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Message",
            placeholder="Ask anything about your project, request a fix, describe a bug...",
            height=72,
            label_visibility="collapsed"
        )
        c1, c2, c3 = st.columns([4, 1, 1])
        submitted = c1.form_submit_button("Send ↵", type="primary", use_container_width=True)
        gen_btn   = c2.form_submit_button("Generate", use_container_width=True)
        fix_btn   = c3.form_submit_button("Fix Errors", use_container_width=True)

    if submitted or gen_btn or fix_btn:
        if not user_input.strip():
            st.warning("Enter a message.")
            return

        task = user_input.strip()

        if gen_btn:
            intent = "build"
        elif fix_btn:
            intent = "debug"
        else:
            if is_casual(task):
                intent = "casual"
            else:
                intent = classify(task)

        s.update_mode(intent)
        s.add_turn("user", task)

        # Only provide project context for non-casual intents
        # Casual greetings should not trigger code analysis
        context = ""
        if intent != "casual" and s.project_loaded and s.project_map and s.file_contents:
            context = select_context(task, s.project_map, s.file_contents)
            mem = s.get_memory_context(task)
            if mem:
                context = mem + "\n\n" + context

        log_placeholder = st.empty()
        steps_seen = []

        def on_step(name):
            steps_seen.append(name)
            log_placeholder.markdown(
                " → ".join(
                    f'<span class="badge badge-info">{n}</span>' for n in steps_seen
                ),
                unsafe_allow_html=True
            )

        try:
            chat_mode = getattr(s, 'chat_mode', 'mixed')
            result, log = run_pipeline(
                task=task,
                intent=intent,
                context=context,
                history=s.history[-10:],
                api_key=api_key,
                yield_steps=on_step,
                chat_mode=chat_mode,
            )
            log_placeholder.empty()
            _handle_result(result, task, intent, s)
        except RuntimeError as e:
            log_placeholder.empty()
            st.error(f"Pipeline error: {e}")
            s.add_turn("assistant", f"Error: {e}")


def _handle_result(result: dict, task: str, intent: str, s: EtherSession):
    rtype = result.get("type", "")

    if rtype == "chat":
        text = result.get("text", "")
        s.add_turn("assistant", text)
        st.rerun()
        return

    if rtype == "debug":
        cause = result.get("root_cause", "")
        explanation = result.get("explanation", "")
        changes = result.get("changes", [])
        reply = f"Root cause: {cause}\n\n{explanation}"
        s.add_turn("assistant", reply)
        if changes:
            previews = preview_changes(changes, s.file_contents)
            st.session_state["pending_changes"] = previews
            st.session_state["pending_raw"] = changes
            remember(task, intent, True, tags=["debug"])
        st.rerun()
        return

    if rtype == "build":
        thought = result.get("thought", {})
        summary = result.get("summary", "")
        changes = result.get("changes", [])
        reply = f"Built: {summary}"
        if thought.get("approach"):
            reply = f"Approach: {thought['approach']}\n\n" + reply
        s.add_turn("assistant", reply)
        if changes:
            previews = preview_changes(changes, s.file_contents)
            st.session_state["pending_changes"] = previews
            st.session_state["pending_raw"] = changes
            remember(task, intent, True, tags=list(thought.get("missing", [])))
        st.rerun()
        return

    s.add_turn("assistant", str(result)[:400])
    st.rerun()


# ── Apply Tab ──────────────────────────────────────────────────────────────────

def _tab_apply():
    s = _session()
    pending = _pending()
    raw_changes = st.session_state.get("pending_raw", [])

    if not pending:
        st.info("No pending changes.")
        return

    st.markdown(f"### {len(pending)} pending change(s)")

    for i, p in enumerate(pending):
        is_new = p["is_new"]
        badge = "badge-warn" if is_new else "badge-info"
        label = "NEW" if is_new else "MODIFY"
        st.markdown(
            f'<span class="badge {badge}">{label}</span> `{p["file"]}` — {p["line_count"]} lines',
            unsafe_allow_html=True
        )
        with st.expander(f"Diff — {p['file']}", expanded=i == 0):
            lines = p["diff"].splitlines()
            rendered = []
            for line in lines[:80]:
                if line.startswith("+") and not line.startswith("+++"):
                    rendered.append(f'<span class="diff-add">{line}</span>')
                elif line.startswith("-") and not line.startswith("---"):
                    rendered.append(f'<span class="diff-rem">{line}</span>')
                else:
                    rendered.append(f'<span class="diff-ctx">{line}</span>')
            st.markdown("<pre>" + "\n".join(rendered) + "</pre>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✓ Apply all", type="primary", use_container_width=True):
            if not s.project_loaded:
                st.error("Load a project first.")
                return
            ok, msg, updated = apply_changes(raw_changes, s.file_contents)
            if ok:
                s.file_contents = updated
                s.project_files = list(updated.keys())
                s.project_map = build_project_map(updated)
                st.session_state["pending_changes"] = []
                st.session_state["pending_raw"] = []
                s.add_turn("assistant", f"Applied: {msg}")
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    with col2:
        if st.button("✗ Discard", use_container_width=True):
            st.session_state["pending_changes"] = []
            st.session_state["pending_raw"] = []
            st.rerun()


# ── Files Tab ──────────────────────────────────────────────────────────────────

def _tab_files():
    s = _session()
    if not s.project_loaded:
        st.info("Load a project to browse files.")
        return
    if not s.project_files or not s.file_contents:
        st.warning("Project file list is empty. Re-upload ZIP.")
        return

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("**Files**")
        selected = st.radio(
            "file", options=s.project_files, label_visibility="collapsed",
            index=s.project_files.index(s.active_file)
            if s.active_file and s.active_file in s.project_files else 0
        )
        s.active_file = selected
    with c2:
        if selected and selected in s.file_contents:
            content = s.file_contents[selected]
            ext = selected.rsplit(".", 1)[-1]
            lang = "gdscript" if ext == "gd" else "text"
            # Show issue badges if any
            script_data = s.project_map.get("scripts", {}).get(selected, {})
            issues = script_data.get("issues", [])
            improvements = script_data.get("improvements", [])
            st.markdown(f"**`{selected}`** — {len(content.splitlines())} lines")
            if issues:
                for iss in issues:
                    st.markdown(f'<span class="badge badge-err">⚠ {iss}</span>', unsafe_allow_html=True)
            if improvements:
                for imp in improvements:
                    st.markdown(f'<span class="badge badge-warn">◈ {imp}</span>', unsafe_allow_html=True)
            st.code(content, language=lang)


# ── Memory Tab ─────────────────────────────────────────────────────────────────

def _tab_memory():
    from core.state import load_memory
    entries = load_memory()
    if not entries:
        st.info("No memory yet.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Total", len(entries))
    c2.metric("Success", sum(1 for e in entries if e.get("success")))
    c3.metric("Failed", sum(1 for e in entries if not e.get("success")))
    st.divider()

    for e in reversed(entries[-30:]):
        ok = e.get("success", False)
        icon = "✓" if ok else "✗"
        cls = "badge-ok" if ok else "badge-err"
        tags = " ".join(f'<span class="badge badge-info">{t}</span>' for t in e.get("tags", []))
        st.markdown(
            f'<span class="badge {cls}">{icon}</span> **{e.get("task","")[:100]}** '
            f'<span style="color:var(--muted);font-size:0.7rem;font-family:monospace;">'
            f'{e.get("ts","")} · {e.get("intent","")}</span> {tags}',
            unsafe_allow_html=True
        )


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    _sidebar()

    # Main area header
    st.markdown("""
    <div style="display:flex;align-items:baseline;gap:0.75rem;margin-bottom:0.25rem;">
        <span style="font-family:'Space Mono',monospace;font-size:0.65rem;
                     letter-spacing:0.18em;color:#4a4a64;">WORKSPACE</span>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["CHAT", "APPLY", "FILES", "MEMORY"])
    with tabs[0]: _tab_chat()
    with tabs[1]: _tab_apply()
    with tabs[2]: _tab_files()
    with tabs[3]: _tab_memory()


if __name__ == "__main__":
    main()
