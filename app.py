"""
Ether — Godot AI Development Assistant
SMGA 3.0 restructured. One file, one loop, one purpose.

Run: streamlit run app.py
"""

import json
import time
import streamlit as st
from pathlib import Path

from core import (
    EtherSession,
    classify,
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
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --bg:       #0a0a0c;
    --surface:  #111116;
    --border:   #1e1e28;
    --accent:   #6e6af0;
    --accent2:  #9d8ff0;
    --text:     #c8c8d4;
    --muted:    #54546a;
    --success:  #4ade80;
    --warn:     #facc15;
    --danger:   #f87171;
    --mono:     'DM Mono', monospace;
    --sans:     'DM Sans', sans-serif;
}

html, body, [class*="css"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--sans) !important;
}

.stApp { background: var(--bg) !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

/* Input */
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

/* Buttons */
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

/* Primary button */
.stButton > button[kind="primary"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: #fff !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--accent2) !important;
    border-color: var(--accent2) !important;
}

/* Tabs */
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

/* Code blocks */
code, pre {
    font-family: var(--mono) !important;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    color: var(--text) !important;
}

/* Chat bubbles */
.msg-user {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 4px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
    font-size: 0.88rem;
}
.msg-ai {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--success);
    border-radius: 4px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
    font-size: 0.88rem;
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

/* Diff */
.diff-add { color: var(--success); font-family: var(--mono); font-size: 0.78rem; }
.diff-rem { color: var(--danger); font-family: var(--mono); font-size: 0.78rem; }
.diff-ctx { color: var(--muted); font-family: var(--mono); font-size: 0.78rem; }

/* Metrics */
.stMetric label { color: var(--muted) !important; font-size: 0.7rem !important; }
.stMetric div[data-testid="metric-container"] > div { color: var(--text) !important; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* Divider */
hr { border-color: var(--border) !important; }

/* Select */
.stSelectbox > div > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    color: var(--muted) !important;
    border-radius: 4px !important;
}

/* Status badges */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-family: var(--mono);
    font-size: 0.68rem;
    letter-spacing: 0.08em;
}
.badge-ok   { background: rgba(74,222,128,0.1); color: var(--success); border: 1px solid rgba(74,222,128,0.25); }
.badge-warn { background: rgba(250,204,21,0.1); color: var(--warn);    border: 1px solid rgba(250,204,21,0.25); }
.badge-err  { background: rgba(248,113,113,0.1); color: var(--danger); border: 1px solid rgba(248,113,113,0.25); }
.badge-info { background: rgba(110,106,240,0.1); color: var(--accent2); border: 1px solid rgba(110,106,240,0.25); }
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
    """
    Resolve API key from:
    1. Session state (primary)
    2. Backward compatibility key
    3. Streamlit secrets.toml
    4. Environment variable
    """

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

    raise RuntimeError("API key not found. Set it in sidebar or secrets.toml.")


# ── Sidebar ────────────────────────────────────────────────────────────────────

def _sidebar():
    s = _session()
    with st.sidebar:
        st.markdown("### ◈ Ether")
        st.markdown(
            '<span class="badge badge-info">SMGA 3.0</span>',
            unsafe_allow_html=True
        )
        st.divider()

        # API Key - use a unique key to avoid state conflicts
        api_key = st.text_input(
            "OpenRouter API Key",
            type="password",
            value="",
            placeholder="sk-or-...",
            help="Free tier at openrouter.ai",
            key="sidebar_api_key"
        )
        # Update session state if user entered a key
        if api_key:
            st.session_state["api_key"] = api_key
        
        # Show status indicator
        if st.session_state.get("api_key", ""):
            st.success("✓ API key set")
        else:
            st.warning("API key required")

        st.divider()

        # Project upload
        st.markdown("**Project**")
        uploaded = st.file_uploader(
            "Upload ZIP", type=["zip"], label_visibility="collapsed"
        )
        if uploaded:
            _handle_upload(uploaded, s)

        if s.project_loaded and s.project_map:
            pm = s.project_map
            stats = pm.get("stats", {})
            c1, c2 = st.columns(2)
            c1.metric("Scripts", stats.get("script_count", 0))
            c2.metric("Scenes", stats.get("scene_count", 0))

            # Active file selector
            if s.project_files:
                active = st.selectbox(
                    "Active file",
                    options=["(none)"] + s.project_files,
                    index=0 if not s.active_file else
                          (s.project_files.index(s.active_file) + 1
                           if s.active_file in s.project_files else 0)
                )
                s.active_file = None if active == "(none)" else active
        else:
            st.caption("No project loaded")

        st.divider()

        # Session info
        st.markdown(f"**Mode** `{s.mode}`")
        st.markdown(f"**Turns** `{len(s.history) // 2}`")

        if st.button("Clear session", use_container_width=True):
            st.session_state["ether"] = EtherSession()
            st.session_state["pending_changes"] = []
            st.rerun()


def _handle_upload(uploaded, s: EtherSession):
    data = uploaded.read()
    if not data:
        st.sidebar.error("Empty ZIP.")
        return
    ok, msg, file_contents = extract_zip(data)
    if not ok:
        st.sidebar.error(msg)
        return
    pm = build_project_map(file_contents)
    s.project_loaded = True
    s.project_files = list(file_contents.keys())
    s.file_contents = file_contents
    s.project_map = pm
    s.active_file = None
    st.sidebar.success(f"✓ {msg}")
    s.add_turn("assistant", f"Project loaded: {pm['stats']['script_count']} scripts, {pm['stats']['scene_count']} scenes.")
    # Force a rerun to ensure the sidebar state is properly updated
    st.rerun()


# ── Tabs ───────────────────────────────────────────────────────────────────────

def _tab_chat():
    s = _session()

    # Render history
    for turn in s.history:
        role = turn["role"]
        content = turn["content"]
        if role == "user":
            st.markdown(f'<div class="msg-user">**you** — {content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="msg-ai">**ether** — {content}</div>', unsafe_allow_html=True)

    # Pending changes banner
    pending = _pending()
    if pending:
        st.divider()
        st.markdown(f'<span class="badge badge-warn">⚠ {len(pending)} pending change(s) — review in Apply tab</span>', unsafe_allow_html=True)
        st.divider()

    # Input
    st.markdown("")
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
        
        # Get API key at submission time from session state
        try:
            api_key = _get_api_key()
        except RuntimeError as e:
            st.error(str(e))

            # Fallback API input (when sidebar is hidden)
            st.markdown("### 🔑 Enter API Key")
            fallback_key = st.text_input(
                "OpenRouter API Key",
                type="password",
                key="fallback_api_key"
            )

            if fallback_key:
                st.session_state["api_key"] = fallback_key
                st.success("API key set. You can continue.")
                st.rerun()

            return

        task = user_input.strip()

        # Force intent for quick-action buttons
        if gen_btn:
            intent = "build"
        elif fix_btn:
            intent = "debug"
        else:
            intent = classify(task)

        s.update_mode(intent)
        s.add_turn("user", task)

        # Context selection - only if project is properly loaded
        context = ""
        if s.project_loaded and s.project_map and s.file_contents:
            context = select_context(task, s.project_map, s.file_contents)
            mem = s.get_memory_context(task)
            if mem:
                context = mem + "\n\n" + context
        elif s.project_loaded:
            st.warning("Project loaded but map is empty. Try re-uploading the ZIP file.")

        # Run
        log_placeholder = st.empty()
        steps_seen = []

        def on_step(name):
            steps_seen.append(name)
            log_placeholder.markdown(
                " → ".join(f'<span class="badge badge-info">{n}</span>' for n in steps_seen),
                unsafe_allow_html=True
            )

        try:
            result, log = run_pipeline(
                task=task,
                intent=intent,
                context=context,
                history=s.history[-10:],
                api_key=api_key,
                yield_steps=on_step,
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

        reply = f"**Root cause:** {cause}\n\n{explanation}"
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

        reply = f"**Built:** {summary}"
        if thought.get("approach"):
            reply = f"**Approach:** {thought['approach']}\n\n" + reply
        s.add_turn("assistant", reply)

        if changes:
            previews = preview_changes(changes, s.file_contents)
            st.session_state["pending_changes"] = previews
            st.session_state["pending_raw"] = changes
            remember(task, intent, True, tags=list(thought.get("missing", [])))
            st.rerun()
        return

    # Fallback
    s.add_turn("assistant", str(result)[:400])
    st.rerun()


def _tab_apply():
    s = _session()
    pending = _pending()
    raw_changes = st.session_state.get("pending_raw", [])

    if not pending:
        st.info("No pending changes. Generate a system or fix errors first.")
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
        st.markdown("")

    col1, col2 = st.columns([1, 1])
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


def _tab_files():
    s = _session()
    if not s.project_loaded:
        st.info("Load a project to browse files.")
        return
    
    if not s.project_files or not s.file_contents:
        st.warning("Project file list is empty. Please re-upload your ZIP file.")
        return

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("**Files**")
        selected = st.radio(
            "file",
            options=s.project_files,
            label_visibility="collapsed",
            index=s.project_files.index(s.active_file) if s.active_file and s.active_file in s.project_files else 0
        )
        s.active_file = selected

    with c2:
        if selected and selected in s.file_contents:
            content = s.file_contents[selected]
            ext = selected.rsplit(".", 1)[-1]
            lang = "gdscript" if ext == "gd" else "text"
            st.markdown(f"**`{selected}`** — {len(content.splitlines())} lines")
            st.code(content, language=lang)


def _tab_map():
    s = _session()
    if not s.project_loaded:
        st.info("Load a project to view the project map.")
        return
    
    if not s.project_map or not s.file_contents:
        st.warning("Project data is incomplete. Please re-upload your ZIP file.")
        return

    pm = s.project_map
    stats = pm.get("stats", {})

    c1, c2, c3 = st.columns(3)
    c1.metric("Scripts", stats.get("script_count", 0))
    c2.metric("Scenes", stats.get("scene_count", 0))
    c3.metric("Total files", stats.get("total_files", 0))
    st.divider()

    if pm.get("scripts"):
        st.markdown("**Scripts**")
        for path, data in pm["scripts"].items():
            with st.expander(path, expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"`extends` **{data.get('extends', '—')}**")
                    if data.get("functions"):
                        st.markdown("**Functions:** " + ", ".join(f"`{f}`" for f in data["functions"]))
                    if data.get("signals"):
                        st.markdown("**Signals:** " + ", ".join(f"`{s}`" for s in data["signals"]))
                with col2:
                    if data.get("tags"):
                        tags_html = " ".join(
                            f'<span class="badge badge-info">{t}</span>' for t in data["tags"]
                        )
                        st.markdown(tags_html, unsafe_allow_html=True)

    if pm.get("scenes"):
        st.divider()
        st.markdown("**Scenes**")
        for path, data in pm["scenes"].items():
            with st.expander(path, expanded=False):
                if data.get("nodes"):
                    st.markdown("**Nodes:** " + ", ".join(f"`{n}`" for n in data["nodes"][:8]))
                if data.get("scripts"):
                    st.markdown("**Scripts:** " + ", ".join(f"`{s}`" for s in data["scripts"]))


def _tab_memory():
    from core.state import load_memory
    entries = load_memory()
    if not entries:
        st.info("No memory yet. Use the assistant to build history.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Total", len(entries))
    c2.metric("Success", sum(1 for e in entries if e.get("success")))
    c3.metric("Failed",  sum(1 for e in entries if not e.get("success")))
    st.divider()

    for e in reversed(entries[-30:]):
        ok = e.get("success", False)
        icon = "✓" if ok else "✗"
        cls = "badge-ok" if ok else "badge-err"
        tags = " ".join(f'<span class="badge badge-info">{t}</span>' for t in e.get("tags", []))
        st.markdown(
            f'<span class="badge {cls}">{icon}</span> **{e.get("task","")[:100]}** '
            f'<span style="color:var(--muted);font-size:0.72rem;font-family:var(--mono);">'
            f'{e.get("ts","")} · {e.get("intent","")}</span> {tags}',
            unsafe_allow_html=True
        )


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    _sidebar()

    # Header
    st.markdown(
        '<h2 style="font-family:\'DM Mono\',monospace;font-weight:300;'
        'letter-spacing:0.12em;color:#6e6af0;margin-bottom:0;">◈ ETHER</h2>'
        '<p style="color:#54546a;font-family:\'DM Mono\',monospace;font-size:0.72rem;'
        'letter-spacing:0.15em;margin-top:2px;">GODOT DEVELOPMENT ASSISTANT</p>',
        unsafe_allow_html=True
    )
    st.markdown("")

    tabs = st.tabs(["CHAT", "APPLY", "FILES", "MAP", "MEMORY"])
    with tabs[0]: _tab_chat()
    with tabs[1]: _tab_apply()
    with tabs[2]: _tab_files()
    with tabs[3]: _tab_map()
    with tabs[4]: _tab_memory()


if __name__ == "__main__":
    main()
