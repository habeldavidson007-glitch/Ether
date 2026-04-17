"""
Ether v1.3 — Godot AI Development Assistant
============================================
Local mode: Ollama backend. No API key. No internet.

OPTIMIZATIONS:
1. Intent-Aware Routing: Greetings respond in <2 seconds via fast path
2. Lazy Loading: Project files loaded on-demand, not all at once
3. Cached Intelligence: Repeated queries return instantly from cache

Run: streamlit run app.py
Requires: ollama serve && ollama pull qwen2.5:3b-instruct-q4_K_M
"""

import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
from typing import Dict, List, Any

# Import EtherBrain - the new optimized engine
from core.builder import EtherBrain

# ── Config ─────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Ether v1.3",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
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

/* ── Chat scroll container ── */
.chat-scroll-container {
    height: calc(100vh - 280px);
    min-height: 300px;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 0.5rem;
    display: flex;
    flex-direction: column;
    gap: 6px;
    scrollbar-width: thin;
    scrollbar-color: var(--border2) transparent;
}
.chat-scroll-container::-webkit-scrollbar { width: 4px; }
.chat-scroll-container::-webkit-scrollbar-track { background: transparent; }
.chat-scroll-container::-webkit-scrollbar-thumb {
    background: var(--border2);
    border-radius: 2px;
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    border-radius: 4px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(110,106,240,0.15) !important;
}

.stButton > button {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.05em !important;
    border-radius: 4px !important;
    transition: border-color 0.15s, color 0.15s !important;
}
.stButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent2) !important;
}
.stButton > button[kind="primary"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: #fff !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    font-family: var(--mono) !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.06em !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.5rem 1.2rem !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent2) !important;
    border-bottom-color: var(--accent) !important;
}

code, pre {
    font-family: var(--mono) !important;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    color: var(--text) !important;
}

.msg-user {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 4px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
    font-size: 0.88rem;
    word-wrap: break-word;
    white-space: pre-wrap;
}
.msg-ai {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--success);
    border-radius: 4px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
    font-size: 0.88rem;
    word-wrap: break-word;
    white-space: pre-wrap;
}
.msg-system {
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.4rem 0.8rem;
    margin: 0.3rem 0;
    font-size: 0.75rem;
    color: var(--muted);
    font-family: var(--mono);
}

.diff-add { color: var(--success); font-family: var(--mono); font-size: 0.78rem; }
.diff-rem { color: var(--danger);  font-family: var(--mono); font-size: 0.78rem; }
.diff-ctx { color: var(--muted);   font-family: var(--mono); font-size: 0.78rem; }

.stMetric label { color: var(--muted) !important; font-size: 0.7rem !important; }

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

hr { border-color: var(--border) !important; }

.stSelectbox > div > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}
.streamlit-expanderHeader {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    color: var(--muted) !important;
    border-radius: 4px !important;
}

.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-family: var(--mono);
    font-size: 0.68rem;
    letter-spacing: 0.08em;
}
.badge-ok   { background: rgba(74,222,128,0.1);  color: var(--success); border: 1px solid rgba(74,222,128,0.25); }
.badge-warn { background: rgba(250,204,21,0.1);  color: var(--warn);    border: 1px solid rgba(250,204,21,0.25); }
.badge-err  { background: rgba(248,113,113,0.1); color: var(--danger);  border: 1px solid rgba(248,113,113,0.25); }
.badge-info { background: rgba(110,106,240,0.1); color: var(--accent2); border: 1px solid rgba(110,106,240,0.25); }
.badge-fast { background: rgba(61,220,132,0.1);  color: var(--success); border: 1px solid rgba(61,220,132,0.25); }

/* Pending changes panel */
.changes-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--warn);
    border-radius: 4px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
}
</style>
""", unsafe_allow_html=True)


# ── Session State Helpers ──────────────────────────────────────────────────────

def _get_brain() -> EtherBrain:
    """Get or create the EtherBrain instance."""
    if "ether_brain" not in st.session_state:
        st.session_state["ether_brain"] = EtherBrain()
    return st.session_state["ether_brain"]


def _pending() -> list:
    """Get pending changes list."""
    if "pending_changes" not in st.session_state:
        st.session_state["pending_changes"] = []
    return st.session_state["pending_changes"]


# ── Upload Handler ─────────────────────────────────────────────────────────────

def _handle_upload(uploaded, brain: EtherBrain):
    """Handle ZIP file upload with lazy loading."""
    data = uploaded.read()
    if not data:
        st.error("Empty ZIP.")
        return False
    
    success, msg = brain.load_project_from_zip(data)
    
    if success:
        stats = brain.project_stats
        st.success(f"✓ {msg}")
        brain.add_to_history("assistant", 
            f"Project loaded: {stats['script_count']} scripts, {stats['scene_count']} scenes. "
            f"(Lazy loaded - files read on demand)")
        return True
    else:
        st.error(msg)
        return False


def _get_uploaded_file_key(uploaded) -> str:
    return f"{uploaded.name}:{uploaded.size}"


# ── Pending Changes (inline in Chat tab) ──────────────────────────────────────

def _render_pending_changes(brain: EtherBrain):
    """Render pending code changes panel."""
    pending = _pending()
    raw_changes = st.session_state.get("pending_raw", [])
    if not pending:
        return

    st.markdown(f'<div class="changes-panel"><b>⚠ {len(pending)} pending change(s)</b></div>', unsafe_allow_html=True)

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

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("✓ Apply all", type="primary", use_container_width=True):
            if not brain.project_loader:
                st.error("Load a project first.")
                return
            ok, msg, updated = _apply_changes(raw_changes, brain.project_loader)
            if ok:
                brain.project_stats = brain.project_loader.get_stats()
                st.session_state["pending_changes"] = []
                st.session_state["pending_raw"] = []
                brain.add_to_history("assistant", f"Applied: {msg}")
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    with col2:
        if st.button("✗ Discard", use_container_width=True):
            st.session_state["pending_changes"] = []
            st.session_state["pending_raw"] = []
            st.rerun()

    st.divider()


def _apply_changes(changes: List[Dict], loader) -> tuple:
    """Apply changes to the workspace."""
    try:
        from core.safety import apply_changes as safety_apply
        
        # Get current file contents from loader
        file_contents = {}
        for path in loader.get_all_paths():
            content = loader.get_content(path)
            if content:
                file_contents[path] = content
        
        ok, msg, updated = safety_apply(changes, file_contents)
        
        if ok:
            # Reload project to pick up changes
            loader.file_index.clear()
            loader.content_cache.clear()
            for path, new_content in updated.items():
                ext = Path(path).suffix
                type_map = {".gd": "script", ".tscn": "scene", ".tres": "resource"}
                loader._raw_file_contents[path] = new_content.encode('utf-8')
                loader.file_index[path] = {
                    "size": len(new_content),
                    "ext": ext,
                    "type": type_map.get(ext, "other"),
                    "loaded": True,
                }
        
        return ok, msg, updated
    except Exception as e:
        return False, f"Apply error: {e}", {}


def _preview_changes(changes: List[Dict], loader) -> List[Dict]:
    """Generate diff previews."""
    try:
        from core.safety import preview_changes as safety_preview
        
        file_contents = {}
        for path in loader.get_all_paths():
            content = loader.get_content(path)
            if content:
                file_contents[path] = content
        
        return safety_preview(changes, file_contents)
    except Exception:
        return []


# ── Chat Tab ───────────────────────────────────────────────────────────────────

def _tab_chat():
    """Main chat interface."""
    brain = _get_brain()

    # ── Mode selector row ──
    mode_labels = {"coding": "⌨ Coding", "general": "◎ General", "mixed": "⊕ Mixed"}
    current_mode = brain.chat_mode

    cols = st.columns([1, 1, 1, 3])
    mode_changed = False
    for i, (k, label) in enumerate(mode_labels.items()):
        with cols[i]:
            active = "primary" if current_mode == k else "secondary"
            if st.button(label, key=f"mode_{k}", type=active if current_mode == k else "secondary",
                         use_container_width=True):
                brain.set_chat_mode(k)
                mode_changed = True

    if mode_changed:
        st.rerun()

    # Render history in scrollable container
    chat_html_parts = []
    for turn in brain.history:
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

    all_msgs = "\n".join(chat_html_parts)
    
    # Scrollable chat container using components.html
    scroll_id = "chat_scroll_bottom"
    components.html(f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Space+Mono&display=swap" rel="stylesheet">
    <style>
    * {{ box-sizing: border-box; }}
    body {{ margin:0; padding:0; background:#07070a; }}
    .chat-wrap {{
        height: calc(100vh - 280px);
        min-height: 300px;
        overflow-y: auto;
        overflow-x: hidden;
        padding: 0.5rem;
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
        font-family: 'Space Mono', monospace; color: #c4c4d4;
        word-wrap: break-word; white-space: pre-wrap;
    }}
    .msg-ai {{
        background: #0e0e14; border: 1px solid #1c1c28;
        border-left: 3px solid #3ddc84; border-radius: 6px;
        padding: 0.6rem 0.85rem; font-size: 0.83rem;
        font-family: 'Space Mono', monospace; color: #c4c4d4;
        word-wrap: break-word; white-space: pre-wrap;
    }}
    .msg-label {{
        font-size: 0.65rem; color: #4a4a64; letter-spacing: 0.1em;
        margin-bottom: 4px; font-family: 'Space Mono', monospace;
    }}
    </style>
    <div class="chat-wrap">{all_msgs}<div id="{scroll_id}"></div></div>
    <script>
    const el = document.getElementById('{scroll_id}');
    if(el) el.scrollIntoView({{behavior:'smooth'}});
    </script>
    """, height=max(300, min(600, 200 + len(brain.history) * 60)), scrolling=False)

    # Pending changes inline
    _render_pending_changes(brain)

    # Upload trigger
    colA, colB = st.columns([6, 1])
    with colB:
        if st.button("＋", help="Upload project ZIP"):
            st.session_state["show_upload"] = True

    if st.session_state.get("show_upload", False):
        uploaded = st.file_uploader("Upload ZIP", type=["zip"], key="chat_upload")
        if uploaded is not None:
            key = _get_uploaded_file_key(uploaded)
            if st.session_state.get("last_uploaded_file_key") != key:
                success = _handle_upload(uploaded, brain)
                if success:
                    st.session_state["last_uploaded_file_key"] = key
                    st.session_state["show_upload"] = False
                    st.rerun()
            else:
                st.session_state["show_upload"] = False

    # Input form
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Message",
            placeholder="Ask anything, request a system, describe a bug...",
            height=80,
            label_visibility="collapsed"
        )
        c1, c2, c3 = st.columns([2, 1, 1])
        submitted = c1.form_submit_button("Send ↵", type="primary", use_container_width=True)
        gen_btn   = c2.form_submit_button("Generate System", use_container_width=True)
        fix_btn   = c3.form_submit_button("Fix Errors", use_container_width=True)

    if submitted or gen_btn or fix_btn:
        if not user_input.strip():
            st.warning("Enter a message.")
            return

        task = user_input.strip()

        # gen_btn / fix_btn force a specific intent and bypass EtherBrain routing.
        # submitted uses EtherBrain's own intent detection (process_query).
        if gen_btn or fix_btn:
            forced_intent = "build" if gen_btn else "debug"
            brain.add_to_history("user", task)

            log_placeholder = st.empty()
            steps_seen = []

            def on_step_forced(name):
                steps_seen.append(name)
                badge_class = "badge-fast" if "Fast path" in name or "Cache hit" in name else "badge-info"
                log_placeholder.markdown(
                    " → ".join(f'<span class="badge {badge_class}">{n}</span>' for n in steps_seen),
                    unsafe_allow_html=True
                )

            try:
                from core.builder import run_pipeline
                context = ""
                if brain.project_loader:
                    context = brain.project_loader.build_lightweight_context(task)
                result, log = run_pipeline(
                    task=task, intent=forced_intent, context=context,
                    history=brain.history[-10:], chat_mode=brain.chat_mode,
                    yield_steps=on_step_forced,
                )
                log_placeholder.empty()
                _handle_result(result, task, brain)
            except Exception as e:
                log_placeholder.empty()
                st.error(f"Pipeline error: {e}")
                brain.add_to_history("assistant", f"Error: {e}")

        else:
            # Normal submit — EtherBrain routes by detected intent
            brain.add_to_history("user", task)

            log_placeholder = st.empty()
            steps_seen = []

            def on_step(name):
                steps_seen.append(name)
                badge_class = "badge-fast" if "Fast path" in name or "Cache hit" in name else "badge-info"
                log_placeholder.markdown(
                    " → ".join(f'<span class="badge {badge_class}">{n}</span>' for n in steps_seen),
                    unsafe_allow_html=True
                )

            try:
                result, log = brain.process_query(task, yield_steps=on_step)
                log_placeholder.empty()
                _handle_result(result, task, brain)
            except Exception as e:
                log_placeholder.empty()
                st.error(f"Pipeline error: {e}")
                brain.add_to_history("assistant", f"Error: {e}")


def _handle_result(result: dict, task: str, brain: EtherBrain):
    """Process and display the result from EtherBrain."""
    rtype = result.get("type", "")
    
    # Show cache/fast path indicators
    if result.get("cached"):
        st.toast("⚡ Cache hit!", icon="⚡")
    elif result.get("fast_path"):
        st.toast("⚡ Fast response!", icon="⚡")

    if rtype == "chat":
        brain.add_to_history("assistant", result.get("text", ""))
        st.rerun()
        return

    if rtype == "debug":
        cause = result.get("root_cause", "")
        explanation = result.get("explanation", "")
        changes = result.get("changes", [])
        brain.add_to_history("assistant", f"**Root cause:** {cause}\n\n{explanation}")
        if changes and brain.project_loader:
            previews = _preview_changes(changes, brain.project_loader)
            st.session_state["pending_changes"] = previews
            st.session_state["pending_raw"] = changes
        try:
            from core.state import remember
            remember(task, "debug", bool(changes), tags=["debug"])
        except Exception:
            pass
        st.rerun()
        return

    if rtype == "build":
        thought = result.get("thought", {})
        summary = result.get("summary", "")
        changes = result.get("changes", [])
        reply = f"**Built:** {summary}"
        if thought.get("approach"):
            reply = f"**Approach:** {thought['approach']}\n\n" + reply
        brain.add_to_history("assistant", reply)
        if changes and brain.project_loader:
            previews = _preview_changes(changes, brain.project_loader)
            st.session_state["pending_changes"] = previews
            st.session_state["pending_raw"] = changes
        try:
            from core.state import remember
            tags = list(thought.get("missing", []))
            remember(task, "build", bool(changes), tags=tags)
        except Exception:
            pass
        st.rerun()
        return

    brain.add_to_history("assistant", str(result)[:400])
    st.rerun()


# ── Brain Map Tab ──────────────────────────────────────────────────────────────

def _tab_map():
    """Display project structure and stats."""
    brain = _get_brain()
    
    if not brain.project_loader:
        st.info("Upload a project ZIP (＋ button in Chat) to see the brain map.")
        return

    stats = brain.project_stats

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scripts", stats.get("script_count", 0))
    c2.metric("Scenes", stats.get("scene_count", 0))
    c3.metric("Total Files", stats.get("total_files", 0))
    c4.metric("Loaded in RAM", stats.get("loaded_files", 0), 
              help="Files actually read into memory (lazy loading)")
    
    st.divider()

    # Cache stats
    cache_stats = brain.get_cache_stats()
    st.markdown(f"**Cache:** {cache_stats['entries']}/{cache_stats['max_entries']} entries "
                f"(TTL: 5 minutes)")

    st.divider()

    # Show file index (metadata only, not content)
    if brain.project_loader.file_index:
        st.markdown("**Indexed Files** (click to load content)")
        
        # Group by type
        scripts = [p for p, m in brain.project_loader.file_index.items() if m.get("ext") == ".gd"]
        scenes = [p for p, m in brain.project_loader.file_index.items() if m.get("ext") == ".tscn"]
        others = [p for p in brain.project_loader.file_index.keys() if p not in scripts and p not in scenes]
        
        if scripts:
            with st.expander(f"📜 Scripts ({len(scripts)})"):
                for path in sorted(scripts):
                    meta = brain.project_loader.file_index[path]
                    details = meta.get("details", {})
                    extends = details.get("extends", "?")
                    funcs = details.get("functions", [])
                    tags = details.get("tags", [])
                    
                    st.markdown(f"**{path}**")
                    st.caption(f"extends: {extends} | Size: {meta.get('size', 0)} bytes")
                    if funcs:
                        st.markdown(f"Functions: `{'`, `'.join(funcs[:10])}`")
                    if tags:
                        tag_spans = " ".join(f'<span class="badge badge-info">{t}</span>' for t in tags)
                        st.markdown(tag_spans, unsafe_allow_html=True)
                    st.divider()
        
        if scenes:
            with st.expander(f"🎬 Scenes ({len(scenes)})"):
                for path in sorted(scenes):
                    meta = brain.project_loader.file_index[path]
                    details = meta.get("details", {})
                    nodes = details.get("nodes", [])
                    scene_scripts = details.get("scripts", [])
                    
                    st.markdown(f"**{path}**")
                    st.caption(f"Size: {meta.get('size', 0)} bytes")
                    if nodes:
                        st.markdown(f"Nodes: `{'`, `'.join(nodes[:8])}`")
                    if scene_scripts:
                        st.markdown(f"Attached scripts: `{'`, `'.join(scene_scripts)}`")
                    st.divider()
        
        if others:
            with st.expander(f"📄 Other Files ({len(others)})"):
                for path in sorted(others):
                    meta = brain.project_loader.file_index[path]
                    st.markdown(f"`{path}` — {meta.get('size', 0)} bytes")


# ── Settings Tab ───────────────────────────────────────────────────────────────

def _tab_settings():
    """Display settings and optimization info."""
    brain = _get_brain()
    
    st.markdown("## ⚙️ Settings")
    
    # Cache controls
    st.markdown("### Cached Intelligence Layer")
    cache_stats = brain.get_cache_stats()
    st.write(f"Current entries: {cache_stats['entries']}/{cache_stats['max_entries']}")
    st.caption("Cache TTL: 5 minutes • LRU eviction: least-recently-accessed entry removed when full")
    st.info("🔀 **Distributed Analysis:** Complex analysis splits into 3 micro-calls (Overview → Deep Dive → Recommendations) to reduce timeouts on low-RAM hardware.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑 Clear Cache", use_container_width=True):
            brain.clear_cache()
            st.success("Cache cleared!")
            st.rerun()
    
    # Optimization info
    st.divider()
    st.markdown("### 🚀 Optimizations Active")
    
    st.markdown("""
    **1. Intent-Aware Routing**
    - Greetings, status, help → Fast path (<2s response)
    - Analysis, coding, debugging → Full LLM pipeline
    
    **2. Lazy Loading Architecture**
    - Only file paths indexed at startup
    - Content loaded on-demand when referenced
    - Reduces RAM usage by ~80%
    
    **3. Cached Intelligence**
    - Repeated queries return instantly
    - 5-minute TTL prevents stale responses
    - Project-aware cache invalidation
    """)
    
    # Model info
    st.divider()
    st.markdown("### 🤖 Model Configuration")
    st.markdown("""
    - **Model:** qwen2.5:3b-instruct-q4_K_M (Ollama)
    - **Context Window:** Optimized for better reasoning
    - **Timeout:** 15s (fast) / 60s (normal) / 120s (slow)
    """)


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    st.markdown(
        '<h2 style="font-family:\'DM Mono\',monospace;font-weight:300;'
        'letter-spacing:0.12em;color:#6e6af0;margin-bottom:0;">◈ ETHER v1.3</h2>'
        '<p style="color:#54546a;font-family:\'DM Mono\',monospace;font-size:0.72rem;'
        'letter-spacing:0.15em;margin-top:2px;">OPTIMIZED FOR LOW-RAM LOCAL ENVIRONMENTS</p>',
        unsafe_allow_html=True
    )
    st.markdown("")

    tabs = st.tabs(["CHAT", "BRAIN MAP", "SETTINGS"])
    with tabs[0]: _tab_chat()
    with tabs[1]: _tab_map()
    with tabs[2]: _tab_settings()


if __name__ == "__main__":
    main()
