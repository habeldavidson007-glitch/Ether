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
    """Convert project map into nodes/edges for the brain graph."""
    if not s.project_loaded or not s.project_map:
        return {"nodes": [], "edges": []}

    pm = s.project_map
    nodes = []
    edges = []
    node_ids = {}

    # Script nodes
    for i, (path, data) in enumerate(pm.get("scripts", {}).items()):
        nid = f"s{i}"
        node_ids[path] = nid
        issues = data.get("issues", [])
        improvements = data.get("improvements", [])
        name = Path(path).stem

        if issues:
            color = "#f06e6e"
            status = "error"
            tooltip = "ISSUES:\n" + "\n".join(f"• {x}" for x in issues[:5])
        elif improvements:
            color = "#f5c842"
            status = "improve"
            tooltip = "IMPROVEMENTS:\n" + "\n".join(f"• {x}" for x in improvements[:5])
        else:
            color = "#4a4a64"
            status = "ok"
            tooltip = f"{name}\n{data.get('extends','')}\n{len(data.get('functions',[]))} functions"

        nodes.append({
            "id": nid,
            "label": name,
            "color": color,
            "status": status,
            "tooltip": tooltip,
            "type": "script",
            "functions": len(data.get("functions", [])),
        })

    # Scene nodes
    for i, (path, data) in enumerate(pm.get("scenes", {}).items()):
        nid = f"sc{i}"
        node_ids[path] = nid
        name = Path(path).stem
        nodes.append({
            "id": nid,
            "label": name,
            "color": "#2a3a5a",
            "status": "scene",
            "tooltip": f"Scene: {name}\n{len(data.get('nodes',[]))} nodes",
            "type": "scene",
        })
        # Edge: scene → script
        for script_path in data.get("scripts", []):
            if script_path in node_ids:
                edges.append({"from": nid, "to": node_ids[script_path]})

    # Script extends relationships
    for path, data in pm.get("scripts", {}).items():
        ext = data.get("extends", "")
        if ext:
            for other_path, other_data in pm.get("scripts", {}).items():
                if Path(other_path).stem == ext and path != other_path:
                    if path in node_ids and other_path in node_ids:
                        edges.append({
                            "from": node_ids[path],
                            "to": node_ids[other_path],
                            "dashed": True
                        })

    return {"nodes": nodes, "edges": edges}


def _render_brain_graph(graph_data: dict, height: int = 480):
    """Render Three.js interactive brain graph."""
    nodes_json = json.dumps(graph_data["nodes"])
    edges_json = json.dumps(graph_data["edges"])

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #07070a; overflow: hidden; font-family: 'Space Mono', monospace; }}
#canvas {{ width: 100%; height: {height}px; display: block; }}
#tooltip {{
    position: fixed; pointer-events: none;
    background: rgba(13,13,20,0.95);
    border: 1px solid #2a2a3a;
    border-left: 2px solid #6e6af0;
    color: #c4c4d4;
    font-family: monospace; font-size: 10px;
    padding: 6px 10px; border-radius: 4px;
    white-space: pre; max-width: 240px;
    opacity: 0; transition: opacity 0.15s;
    z-index: 999; line-height: 1.5;
}}
#legend {{
    position: absolute; bottom: 10px; left: 10px;
    display: flex; gap: 10px; align-items: center;
    font-family: monospace; font-size: 9px; color: #4a4a64;
}}
.leg {{ display: flex; align-items: center; gap: 4px; }}
.leg-dot {{ width: 8px; height: 8px; border-radius: 50%; }}
#stats {{
    position: absolute; top: 10px; right: 10px;
    font-family: monospace; font-size: 9px; color: #4a4a64;
    text-align: right; line-height: 1.6;
}}
</style>
</head>
<body>
<canvas id="canvas"></canvas>
<div id="tooltip"></div>
<div id="legend">
    <div class="leg"><div class="leg-dot" style="background:#f06e6e"></div>issues</div>
    <div class="leg"><div class="leg-dot" style="background:#f5c842"></div>improve</div>
    <div class="leg"><div class="leg-dot" style="background:#4a4a64"></div>clean</div>
    <div class="leg"><div class="leg-dot" style="background:#2a3a5a"></div>scene</div>
</div>
<div id="stats"></div>

<script>
const NODES = {nodes_json};
const EDGES = {edges_json};

const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const tooltip = document.getElementById('tooltip');
const statsEl = document.getElementById('stats');

// Canvas sizing
function resize() {{
    canvas.width = canvas.clientWidth;
    canvas.height = {height};
}}
resize();
window.addEventListener('resize', () => {{ resize(); layout(); draw(); }});

// Physics layout
let positions = {{}};
let velocities = {{}};
let dragging = null;
let dragOffset = {{x:0, y:0}};
let mouse = {{x:0, y:0}};
let hoveredNode = null;
let frame = 0;
let pulse = 0;

function layout() {{
    const W = canvas.width, H = canvas.height;
    const cx = W/2, cy = H/2;
    const count = NODES.length;
    NODES.forEach((n, i) => {{
        if (!positions[n.id]) {{
            const angle = (i / count) * Math.PI * 2;
            const r = Math.min(W, H) * 0.3;
            positions[n.id] = {{
                x: cx + Math.cos(angle) * r * (0.6 + Math.random()*0.4),
                y: cy + Math.sin(angle) * r * (0.6 + Math.random()*0.4),
            }};
            velocities[n.id] = {{x: 0, y: 0}};
        }}
    }});
}}

function physics() {{
    const W = canvas.width, H = canvas.height;
    const REPEL = 2200, ATTRACT = 0.012, EDGE_ATTRACT = 0.06, DAMPING = 0.82;

    // Repulsion
    NODES.forEach(a => {{
        NODES.forEach(b => {{
            if (a.id === b.id) return;
            const pa = positions[a.id], pb = positions[b.id];
            if (!pa || !pb) return;
            let dx = pa.x - pb.x, dy = pa.y - pb.y;
            let dist = Math.sqrt(dx*dx + dy*dy) || 1;
            let force = REPEL / (dist * dist);
            velocities[a.id].x += (dx/dist) * force;
            velocities[a.id].y += (dy/dist) * force;
        }});
    }});

    // Edge attraction
    EDGES.forEach(e => {{
        const pa = positions[e.from], pb = positions[e.to];
        if (!pa || !pb) return;
        let dx = pb.x - pa.x, dy = pb.y - pa.y;
        let dist = Math.sqrt(dx*dx + dy*dy);
        let target = 80;
        let force = (dist - target) * EDGE_ATTRACT;
        velocities[e.from].x += (dx/dist) * force;
        velocities[e.from].y += (dy/dist) * force;
        velocities[e.to].x   -= (dx/dist) * force;
        velocities[e.to].y   -= (dy/dist) * force;
    }});

    // Center gravity
    NODES.forEach(n => {{
        const p = positions[n.id];
        if (!p || n.id === dragging) return;
        let dx = canvas.width/2 - p.x, dy = canvas.height/2 - p.y;
        velocities[n.id].x += dx * 0.001;
        velocities[n.id].y += dy * 0.001;
    }});

    // Integrate
    NODES.forEach(n => {{
        if (n.id === dragging) return;
        const p = positions[n.id], v = velocities[n.id];
        if (!p || !v) return;
        v.x *= DAMPING; v.y *= DAMPING;
        p.x += v.x; p.y += v.y;
        p.x = Math.max(30, Math.min(canvas.width-30, p.x));
        p.y = Math.max(30, Math.min(canvas.height-30, p.y));
    }});
}}

function getNodeAt(mx, my) {{
    for (let i = NODES.length-1; i >= 0; i--) {{
        const n = NODES[i];
        const p = positions[n.id];
        if (!p) continue;
        const r = n.type === 'scene' ? 14 : 10;
        let dx = mx - p.x, dy = my - p.y;
        if (dx*dx + dy*dy < r*r*2.5) return n;
    }}
    return null;
}}

function draw() {{
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Background grid
    ctx.strokeStyle = 'rgba(30,30,45,0.4)';
    ctx.lineWidth = 0.5;
    for(let x = 0; x < W; x += 40) {{
        ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke();
    }}
    for(let y = 0; y < H; y += 40) {{
        ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke();
    }}

    // Edges
    EDGES.forEach(e => {{
        const pa = positions[e.from], pb = positions[e.to];
        if (!pa || !pb) return;
        ctx.beginPath();
        ctx.moveTo(pa.x, pa.y);
        ctx.lineTo(pb.x, pb.y);
        if (e.dashed) {{
            ctx.setLineDash([3,5]);
            ctx.strokeStyle = 'rgba(110,106,240,0.2)';
        }} else {{
            ctx.setLineDash([]);
            ctx.strokeStyle = 'rgba(74,74,100,0.5)';
        }}
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.setLineDash([]);
    }});

    // Nodes
    const t = Date.now() / 1000;
    NODES.forEach(n => {{
        const p = positions[n.id];
        if (!p) return;
        const isHovered = hoveredNode && hoveredNode.id === n.id;
        const r = n.type === 'scene' ? 14 : 10;
        const rActual = isHovered ? r * 1.3 : r;

        // Glow for error/improve/hovered
        if (n.status === 'error' || n.status === 'improve' || isHovered) {{
            const glowR = rActual + 8 + Math.sin(t*3)*3;
            const grd = ctx.createRadialGradient(p.x, p.y, rActual, p.x, p.y, glowR);
            let glowColor = n.status === 'error' ? 'rgba(240,110,110,' : 'rgba(245,200,66,';
            if (isHovered) glowColor = 'rgba(110,106,240,';
            grd.addColorStop(0, glowColor + '0.3)');
            grd.addColorStop(1, glowColor + '0)');
            ctx.beginPath();
            ctx.arc(p.x, p.y, glowR, 0, Math.PI*2);
            ctx.fillStyle = grd;
            ctx.fill();
        }}

        // Node body
        ctx.beginPath();
        if (n.type === 'scene') {{
            // Diamond for scenes
            ctx.moveTo(p.x, p.y - rActual);
            ctx.lineTo(p.x + rActual, p.y);
            ctx.lineTo(p.x, p.y + rActual);
            ctx.lineTo(p.x - rActual, p.y);
            ctx.closePath();
        }} else {{
            ctx.arc(p.x, p.y, rActual, 0, Math.PI*2);
        }}
        ctx.fillStyle = n.color;
        ctx.fill();
        ctx.strokeStyle = isHovered ? '#6e6af0' : 'rgba(255,255,255,0.1)';
        ctx.lineWidth = isHovered ? 2 : 1;
        ctx.stroke();

        // Label
        ctx.font = `${{isHovered ? 'bold ' : ''}}9px Space Mono, monospace`;
        ctx.fillStyle = isHovered ? '#fff' : 'rgba(200,200,220,0.7)';
        ctx.textAlign = 'center';
        ctx.fillText(n.label.substring(0,12), p.x, p.y + rActual + 11);
    }});

    // Stats
    const errs = NODES.filter(n => n.status === 'error').length;
    const imps = NODES.filter(n => n.status === 'improve').length;
    const ok   = NODES.filter(n => n.status === 'ok').length;
    statsEl.innerHTML = `${{NODES.length}} nodes · ${{EDGES.length}} edges<br><span style="color:#f06e6e">${{errs}} errors</span> · <span style="color:#f5c842">${{imps}} improve</span> · <span style="color:#4a4a64">${{ok}} clean</span>`;
}}

// Animate
function animate() {{
    frame++;
    if (frame % 2 === 0) physics();
    draw();
    requestAnimationFrame(animate);
}}

// Mouse events
canvas.addEventListener('mousemove', e => {{
    const rect = canvas.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;

    if (dragging) {{
        positions[dragging].x = mouse.x + dragOffset.x;
        positions[dragging].y = mouse.y + dragOffset.y;
        velocities[dragging] = {{x:0, y:0}};
        return;
    }}

    const node = getNodeAt(mouse.x, mouse.y);
    hoveredNode = node;
    if (node) {{
        tooltip.style.left = (e.clientX + 14) + 'px';
        tooltip.style.top  = (e.clientY - 10) + 'px';
        tooltip.textContent = node.tooltip;
        tooltip.style.opacity = '1';
        canvas.style.cursor = 'grab';
    }} else {{
        tooltip.style.opacity = '0';
        canvas.style.cursor = 'default';
    }}
}});

canvas.addEventListener('mousedown', e => {{
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const node = getNodeAt(mx, my);
    if (node) {{
        dragging = node.id;
        dragOffset.x = positions[node.id].x - mx;
        dragOffset.y = positions[node.id].y - my;
        canvas.style.cursor = 'grabbing';
    }}
}});

canvas.addEventListener('mouseup', () => {{
    dragging = null;
    canvas.style.cursor = 'default';
}});

canvas.addEventListener('mouseleave', () => {{
    tooltip.style.opacity = '0';
    hoveredNode = null;
}});

layout();
animate();
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

        # Project upload
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">Project</div>', unsafe_allow_html=True)

        uploaded = st.file_uploader("Upload ZIP", type=["zip"], key="sidebar_upload",
                                     label_visibility="collapsed")
        if uploaded is not None:
            key = _get_uploaded_file_key(uploaded)
            if st.session_state.get("last_uploaded_file_key") != key:
                success = _handle_upload(uploaded, s)
                if success:
                    st.session_state["last_uploaded_file_key"] = key
                    st.rerun()

        if s.project_loaded:
            stats = s.project_map.get("stats", {})
            c1, c2 = st.columns(2)
            c1.metric("Scripts", stats.get("script_count", 0))
            c2.metric("Scenes", stats.get("scene_count", 0))
            c1.metric("Issues", stats.get("total_issues", 0))
            c2.metric("Improve", stats.get("total_improvements", 0))

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
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Message",
            placeholder="Ask anything about your project, request a fix, describe a bug...",
            height=72,
            label_visibility="collapsed"
        )
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        submitted = c1.form_submit_button("Send ↵", type="primary", use_container_width=True)
        gen_btn   = c2.form_submit_button("Generate", use_container_width=True)
        fix_btn   = c3.form_submit_button("Fix Errors", use_container_width=True)
        upload_btn = c4.form_submit_button("＋ ZIP", use_container_width=True)

    if upload_btn:
        st.session_state["show_upload"] = not st.session_state.get("show_upload", False)
        st.rerun()

    if st.session_state.get("show_upload", False):
        up2 = st.file_uploader("Upload ZIP", type=["zip"], key="chat_upload_inline")
        if up2 is not None:
            key = _get_uploaded_file_key(up2)
            if st.session_state.get("last_uploaded_file_key") != key:
                success = _handle_upload(up2, s)
                if success:
                    st.session_state["last_uploaded_file_key"] = key
                    st.session_state["show_upload"] = False
                    st.rerun()

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

        context = ""
        if s.project_loaded and s.project_map and s.file_contents:
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
