"""
Ether — Godot AI Development Assistant
Local mode: Ollama backend. No API key. No internet.

Run: streamlit run app.py
Requires: ollama serve && ollama pull qwen2.5:0.5b

v1.1 — Added: scrollable chat, mode selector (Coding/General/Mixed), expert personas
"""

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


# ── Session ─────────────────────────────────────────────────────────────────────

def _session() -> EtherSession:
    if "ether" not in st.session_state:
        st.session_state["ether"] = EtherSession()
    return st.session_state["ether"]


def _pending() -> list:
    if "pending_changes" not in st.session_state:
        st.session_state["pending_changes"] = []
    return st.session_state["pending_changes"]


# ── Upload Handler ─────────────────────────────────────────────────────────────

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
    s.add_turn("assistant", f"Project loaded: {pm['stats']['script_count']} scripts, {pm['stats']['scene_count']} scenes.")
    return True


def _get_uploaded_file_key(uploaded) -> str:
    return f"{uploaded.name}:{uploaded.size}"


# ── Pending Changes (inline in Chat tab) ──────────────────────────────────────

def _render_pending_changes(s: EtherSession):
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

    st.divider()


# ── Chat Tab ───────────────────────────────────────────────────────────────────

def _tab_chat():
    s = _session()

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

    # Render history in scrollable container
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
    """, height=max(300, min(600, 200 + len(s.history) * 60)), scrolling=False)

    # Pending changes inline
    _render_pending_changes(s)

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
                success = _handle_upload(uploaded, s)
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

        if gen_btn:
            intent = "build"
        elif fix_btn:
            intent = "debug"
        else:
            intent = "casual" if is_casual(task) else classify(task)

        s.update_mode(intent)
        s.add_turn("user", task)

        context = ""
        if s.project_loaded and s.project_map and s.file_contents:
            context = select_context(task, s.project_map, s.file_contents)
            mem = s.get_memory_context(task)
            if mem:
                context = mem + "\n\n" + context

        # Get chat mode for expert persona
        chat_mode = getattr(s, 'chat_mode', 'mixed')

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
                history=s.history[-6:],  # 🔥 Reduced history for speed
                yield_steps=on_step,
                chat_mode=chat_mode,
            )
            log_placeholder.empty()
            _handle_result(result, task, intent, s)

        except Exception as e:
            log_placeholder.empty()
            st.error(f"Pipeline error: {e}")
            s.add_turn("assistant", f"Error: {e}")


def _handle_result(result: dict, task: str, intent: str, s: EtherSession):
    rtype = result.get("type", "")

    if rtype == "chat":
        s.add_turn("assistant", result.get("text", ""))
        st.rerun()
        return

    if rtype == "debug":
        cause = result.get("root_cause", "")
        explanation = result.get("explanation", "")
        changes = result.get("changes", [])
        s.add_turn("assistant", f"**Root cause:** {cause}\n\n{explanation}")
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

    s.add_turn("assistant", str(result)[:400])
    st.rerun()


# ── Brain Map Tab ──────────────────────────────────────────────────────────────

def _tab_map():
    s = _session()
    if not s.project_loaded:
        st.info("Upload a project ZIP (＋ button in Chat) to see the brain map.")
        return

    if not s.project_map or not s.file_contents:
        st.warning("Project data incomplete. Re-upload the ZIP file.")
        return

    pm = s.project_map
    stats = pm.get("stats", {})

    c1, c2, c3 = st.columns(3)
    c1.metric("Scripts", stats.get("script_count", 0))
    c2.metric("Scenes",  stats.get("scene_count", 0))
    c3.metric("Files",   stats.get("total_files", 0))
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
                        st.markdown("**Signals:** " + ", ".join(f"`{sig}`" for sig in data["signals"]))
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
                    st.markdown("**Scripts:** " + ", ".join(f"`{sc}`" for sc in data["scripts"]))


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    st.markdown(
        '<h2 style="font-family:\'DM Mono\',monospace;font-weight:300;'
        'letter-spacing:0.12em;color:#6e6af0;margin-bottom:0;">◈ ETHER</h2>'
        '<p style="color:#54546a;font-family:\'DM Mono\',monospace;font-size:0.72rem;'
        'letter-spacing:0.15em;margin-top:2px;">GODOT DEVELOPMENT ASSISTANT · LOCAL</p>',
        unsafe_allow_html=True
    )
    st.markdown("")

    tabs = st.tabs(["CHAT", "BRAIN MAP"])
    with tabs[0]: _tab_chat()
    with tabs[1]: _tab_map()


if __name__ == "__main__":
    main()
