"""
Vedantu Multi-Agent Marketing System — Streamlit Dashboard
Agent 3: UI/Integration with Human-in-the-Loop controls
"""
import streamlit as st
import json
import os
import time
import tempfile
from datetime import datetime

# Must be first Streamlit command
st.set_page_config(
    page_title="Vedantu AI Video Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from agents import AgentOrchestrator
from config import (
    VEDANTU_BRAND, ARTIFACTS_DIR, MUAPI_API_KEY, GEMINI_API_KEY,
    VIDEO_DURATION_OPTIONS, VIDEO_DURATION_DEFAULT,
    VIDEO_ASPECT_RATIO_OPTIONS, VIDEO_ASPECT_RATIO_DEFAULT,
    VIDEO_QUALITY_OPTIONS, VIDEO_QUALITY_DEFAULT,
)


# ══════════════════════════════════════════════════════════════════════════════
# CSS — Premium Dark Theme
# ══════════════════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* ── Global ──────────────────────────────────────────────────────────── */
    .stApp {
        background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 40%, #16213e 70%, #0f3460 100%);
        font-family: 'Inter', sans-serif;
    }

    .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }

    /* ── Header ──────────────────────────────────────────────────────────── */
    .main-header {
        text-align: center;
        padding: 2rem 0 1rem;
    }
    .main-header h1 {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #4CAF50, #FF9800, #2196F3);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: #a0a0b0;
        font-size: 1rem;
        font-weight: 400;
    }

    /* ── Agent Status Cards ──────────────────────────────────────────────── */
    .agent-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .agent-card {
        background: rgba(22, 33, 62, 0.7);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.2rem;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .agent-card:hover {
        border-color: rgba(76, 175, 80, 0.4);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }
    .agent-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        border-radius: 16px 16px 0 0;
    }
    .agent-card.idle::before { background: linear-gradient(90deg, #555, #777); }
    .agent-card.running::before { background: linear-gradient(90deg, #FF9800, #FFD54F); animation: pulse-bar 1.5s infinite; }
    .agent-card.completed::before { background: linear-gradient(90deg, #4CAF50, #81C784); }
    .agent-card.error::before { background: linear-gradient(90deg, #f44336, #e57373); }

    @keyframes pulse-bar {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    .agent-icon { font-size: 1.6rem; margin-bottom: 0.4rem; }
    .agent-name {
        font-size: 0.85rem;
        font-weight: 600;
        color: #e8e8e8;
        margin-bottom: 0.3rem;
    }
    .agent-status {
        font-size: 0.72rem;
        font-weight: 500;
        padding: 3px 10px;
        border-radius: 20px;
        display: inline-block;
        margin-bottom: 0.4rem;
    }
    .status-idle { background: rgba(85,85,85,0.3); color: #999; }
    .status-running { background: rgba(255,152,0,0.2); color: #FFB74D; }
    .status-completed { background: rgba(76,175,80,0.2); color: #81C784; }
    .status-error { background: rgba(244,67,54,0.2); color: #e57373; }

    .agent-message {
        font-size: 0.7rem;
        color: #888;
        margin-top: 0.3rem;
        line-height: 1.3;
        min-height: 2em;
    }

    /* ── Section Panels ──────────────────────────────────────────────────── */
    .section-panel {
        background: rgba(22, 33, 62, 0.5);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 20px;
        padding: 1.8rem;
        margin-bottom: 1.5rem;
        backdrop-filter: blur(12px);
    }
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #e8e8e8;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .section-title span.icon {
        font-size: 1.2rem;
    }

    /* ── Trend Table ─────────────────────────────────────────────────────── */
    .trend-row {
        display: grid;
        grid-template-columns: 40px 1fr 150px 140px;
        gap: 1rem;
        align-items: center;
        padding: 0.8rem 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
        background: rgba(15, 52, 96, 0.3);
        border: 1px solid rgba(255,255,255,0.04);
        transition: background 0.2s;
    }
    .trend-row:hover {
        background: rgba(15, 52, 96, 0.6);
    }
    .trend-rank {
        font-size: 1.1rem;
        font-weight: 700;
        color: #4CAF50;
        text-align: center;
    }
    .trend-topic {
        font-size: 0.85rem;
        font-weight: 500;
        color: #e0e0e0;
        line-height: 1.3;
    }
    .trend-source {
        font-size: 0.75rem;
        color: #a0a0b0;
        display: flex;
        align-items: center;
        gap: 0.3rem;
    }
    .trend-engagement {
        font-size: 0.75rem;
        font-weight: 600;
        color: #FFB74D;
        text-align: right;
    }

    /* ── Script Cards ────────────────────────────────────────────────────── */
    .script-card {
        background: rgba(15, 52, 96, 0.4);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.3rem;
        margin-bottom: 1rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .script-card:hover, .script-card.selected {
        border-color: rgba(76, 175, 80, 0.5);
        box-shadow: 0 0 20px rgba(76, 175, 80, 0.1);
    }
    .script-label {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
    }
    .script-label.hook { color: #FF9800; }
    .script-label.body { color: #2196F3; }
    .script-label.cta { color: #4CAF50; }
    .script-text {
        font-size: 0.88rem;
        color: #d0d0d0;
        line-height: 1.5;
    }

    /* ── Buttons ──────────────────────────────────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, #4CAF50, #2E7D32) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.7rem 2rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
        letter-spacing: 0.3px !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(76, 175, 80, 0.4) !important;
    }

    /* ── Text Area ───────────────────────────────────────────────────────── */
    .stTextArea textarea {
        background: rgba(15, 52, 96, 0.4) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        color: #e0e0e0 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9rem !important;
        line-height: 1.6 !important;
    }
    .stTextArea textarea:focus {
        border-color: rgba(76, 175, 80, 0.5) !important;
        box-shadow: 0 0 15px rgba(76, 175, 80, 0.1) !important;
    }

    /* ── File Uploader ───────────────────────────────────────────────────── */
    .stFileUploader {
        background: rgba(15, 52, 96, 0.3) !important;
        border-radius: 12px !important;
    }

    /* ── Progress / Spinners ─────────────────────────────────────────────── */
    .stProgress > div > div {
        background: linear-gradient(90deg, #4CAF50, #FF9800) !important;
    }

    /* ── Video Container ─────────────────────────────────────────────────── */
    .video-container {
        background: rgba(15, 52, 96, 0.3);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
    }

    /* ── Status Log ──────────────────────────────────────────────────────── */
    .status-log {
        background: rgba(10, 10, 26, 0.6);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 1rem;
        max-height: 200px;
        overflow-y: auto;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.72rem;
        color: #81C784;
        line-height: 1.8;
    }

    /* ── Divider ──────────────────────────────────────────────────────────── */
    .glow-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(76,175,80,0.3), rgba(255,152,0,0.3), transparent);
        margin: 1.5rem 0;
        border: none;
    }

    /* ── Hide Streamlit defaults ─────────────────────────────────────────── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ── Responsive ──────────────────────────────────────────────────────── */
    @media (max-width: 768px) {
        .agent-grid { grid-template-columns: repeat(2, 1fr); }
        .trend-row { grid-template-columns: 30px 1fr; }
        .trend-source, .trend-engagement { display: none; }
    }
    </style>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Session State Initialization
# ══════════════════════════════════════════════════════════════════════════════
def init_session_state():
    defaults = {
        "pipeline_stage": "ready",       # ready, scraping, scripting, editing, generating, completed
        "trend_report": None,
        "scripts": None,
        "selected_script_idx": 0,
        "edited_script": "",
        "uploaded_image_path": None,
        "video_result": None,
        "agent_statuses": {
            "scraper":  {"name": "Scraper/Scout",     "status": "idle", "icon": "🔍", "last_message": "Waiting to start"},
            "creative": {"name": "Creative Director",  "status": "idle", "icon": "✍️", "last_message": "Waiting for trends"},
            "ui":       {"name": "Dashboard (UI)",     "status": "active", "icon": "🖥️", "last_message": "Ready"},
            "video":    {"name": "Video Producer",     "status": "idle", "icon": "🎬", "last_message": "Waiting for script"},
        },
        "status_log": [],
        "orchestrator": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    if st.session_state.orchestrator is None:
        st.session_state.orchestrator = AgentOrchestrator()


# ══════════════════════════════════════════════════════════════════════════════
# UI Components
# ══════════════════════════════════════════════════════════════════════════════
def render_header():
    st.markdown("""
    <div class="main-header">
        <h1>🎬 Vedantu AI Video Generator</h1>
        <p>Multi-Agent Marketing System — Trend-Driven Promotional Video Creation</p>
    </div>
    """, unsafe_allow_html=True)


def render_agent_status_panel():
    """Render the 4-agent status cards using st.columns for reliable rendering."""
    statuses = st.session_state.agent_statuses
    cols = st.columns(4)

    for col, key in zip(cols, ["scraper", "creative", "ui", "video"]):
        agent = statuses[key]
        status = agent["status"]
        with col:
            st.markdown(f"""
            <div class="agent-card {status}">
                <div class="agent-icon">{agent['icon']}</div>
                <div class="agent-name">{agent['name']}</div>
                <div class="agent-status status-{status}">{status.upper()}</div>
                <div class="agent-message">{agent.get('last_message', '')}</div>
            </div>
            """, unsafe_allow_html=True)


def render_trend_report():
    """Render the trend report as a styled table."""
    report = st.session_state.trend_report
    if not report:
        return

    st.markdown('<div class="section-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title"><span class="icon">📊</span> Trend Report</div>', unsafe_allow_html=True)

    trends = report.get("trends", [])
    for trend in trends:
        source_icon = "🔴" if "Reddit" in trend.get("source", "") else ("🎥" if "YouTube" in trend.get("source", "") else "📸")
        st.markdown(f"""
        <div class="trend-row">
            <div class="trend-rank">#{trend.get('rank', '?')}</div>
            <div class="trend-topic">{trend.get('topic', 'N/A')}<br><span style="font-size:0.7rem;color:#888;">{trend.get('pain_point', '')}</span></div>
            <div class="trend-source">{source_icon} {trend.get('source', 'N/A')}</div>
            <div class="trend-engagement">{trend.get('engagement', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_script_editor():
    """Render the HITL script selection and editing UI."""
    scripts = st.session_state.scripts
    if not scripts:
        return

    st.markdown('<div class="section-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title"><span class="icon">✍️</span> Script Editor — Human-in-the-Loop</div>', unsafe_allow_html=True)

    # Script variant selector
    st.markdown("**Select a script variant to customize:**")
    for i, script in enumerate(scripts):
        st.markdown(f"""
        <div class="script-card {'selected' if i == st.session_state.selected_script_idx else ''}">
            <div class="script-label hook">🎯 HOOK (0-3s)</div>
            <div class="script-text">{script.get('hook', '')}</div>
            <div class="script-label body" style="margin-top:0.6rem;">💡 SOLUTION (3-12s)</div>
            <div class="script-text">{script.get('body', '')}</div>
            <div class="script-label cta" style="margin-top:0.6rem;">🚀 CTA (12-15s)</div>
            <div class="script-text">{script.get('cta', '')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Script variant selection
    cols = st.columns(len(scripts))
    for i, col in enumerate(cols):
        with col:
            if st.button(f"📜 Select Script {i+1}", key=f"select_script_{i}", use_container_width=True):
                st.session_state.selected_script_idx = i
                selected = scripts[i]
                st.session_state.edited_script = selected.get("full_script", "")
                st.rerun()

    st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)

    # Editable script area
    selected_script = scripts[st.session_state.selected_script_idx]
    default_text = st.session_state.edited_script or selected_script.get("full_script", "")

    st.markdown("**✏️ Edit the script below before generating:**")
    edited = st.text_area(
        "Edit Script",
        value=default_text,
        height=150,
        label_visibility="collapsed",
        key="script_editor",
    )
    st.session_state.edited_script = edited

    # Visual direction hint
    vis_dir = selected_script.get("visual_direction", "")
    if vis_dir:
        st.markdown(f"**🎨 Visual Direction:** _{vis_dir}_")

    st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)

    # Image upload
    st.markdown("**🖼️ Upload a reference image (optional):**")
    st.markdown("_Upload a Vedantu product image, logo, or scene to use as a visual reference for video generation._")
    uploaded_file = st.file_uploader(
        "Upload Reference Image",
        type=["png", "jpg", "jpeg", "webp"],
        label_visibility="collapsed",
        key="image_uploader",
    )

    if uploaded_file:
        # Save uploaded file
        img_path = os.path.join(ARTIFACTS_DIR, f"reference_{uploaded_file.name}")
        with open(img_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        st.session_state.uploaded_image_path = img_path
        st.image(uploaded_file, caption="Reference Image", width=300)

    st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)

    # ── Video Generation Settings ─────────────────────────────────────────
    st.markdown("**⚙️ Video Generation Settings:**")
    settings_cols = st.columns(3)
    with settings_cols[0]:
        vid_duration = st.selectbox(
            "Duration (seconds)",
            options=VIDEO_DURATION_OPTIONS,
            index=VIDEO_DURATION_OPTIONS.index(VIDEO_DURATION_DEFAULT),
            key="vid_duration",
        )
    with settings_cols[1]:
        vid_aspect = st.selectbox(
            "Aspect Ratio",
            options=VIDEO_ASPECT_RATIO_OPTIONS,
            index=VIDEO_ASPECT_RATIO_OPTIONS.index(VIDEO_ASPECT_RATIO_DEFAULT),
            key="vid_aspect",
            help="9:16 = Reels/Shorts, 16:9 = YouTube, 1:1 = Square",
        )
    with settings_cols[2]:
        vid_quality = st.selectbox(
            "Quality",
            options=VIDEO_QUALITY_OPTIONS,
            index=VIDEO_QUALITY_OPTIONS.index(VIDEO_QUALITY_DEFAULT),
            key="vid_quality",
        )

    # Store settings in session state
    st.session_state.video_settings = {
        "duration": vid_duration,
        "aspect_ratio": vid_aspect,
        "quality": vid_quality,
    }

    st.markdown("")  # spacing


def render_video_result():
    """Render the generated video preview."""
    result = st.session_state.video_result
    if not result:
        return

    st.markdown('<div class="section-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title"><span class="icon">🎬</span> Generated Video</div>', unsafe_allow_html=True)

    if result.get("status") == "completed":
        video_url = result.get("video_url", "")
        local_path = result.get("local_path", "")

        if local_path and os.path.exists(local_path):
            st.video(local_path)
            with open(local_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Video",
                    data=f.read(),
                    file_name="vedantu_promo.mp4",
                    mime="video/mp4",
                    use_container_width=True,
                )
        elif video_url:
            st.video(video_url)
            st.markdown(f"[🔗 Open video in browser]({video_url})")

        st.success("✅ Video generated successfully!")
    else:
        st.error("❌ Video generation failed. Check the status log for details.")

    st.markdown('</div>', unsafe_allow_html=True)


def render_status_log():
    """Render the real-time status log."""
    log = st.session_state.status_log
    if not log:
        return

    with st.expander("📋 Agent Activity Log", expanded=False):
        log_html = '<div class="status-log">'
        for entry in reversed(log[-50:]):  # last 50 entries
            log_html += f"{entry}<br>"
        log_html += '</div>'
        st.markdown(log_html, unsafe_allow_html=True)


def add_status_log(message):
    """Add a message to the status log."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.status_log.append(f"[{timestamp}] {message}")


def update_agent_ui_status(agent_key, status, message=""):
    """Update an agent's status in the UI."""
    if agent_key in st.session_state.agent_statuses:
        st.session_state.agent_statuses[agent_key]["status"] = status
        st.session_state.agent_statuses[agent_key]["last_message"] = message
    add_status_log(f"{agent_key.upper()}: {message}")


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline Actions
# ══════════════════════════════════════════════════════════════════════════════
def run_scraping_pipeline():
    """Execute Agent 1 → Agent 2 pipeline."""
    orchestrator = st.session_state.orchestrator

    # Agent 1: Scrape
    st.session_state.pipeline_stage = "scraping"
    update_agent_ui_status("scraper", "running", "Starting trend analysis...")

    with st.spinner("🔍 Agent 1 is scanning YouTube, Reddit, Instagram for trends..."):
        def scraper_callback(msg):
            update_agent_ui_status("scraper", "running", msg)

        trend_report = orchestrator.run_scraper(status_callback=scraper_callback)
        st.session_state.trend_report = trend_report
        update_agent_ui_status("scraper", "completed", f"Found {trend_report['total_trends']} trends")

    # Agent 2: Generate scripts
    st.session_state.pipeline_stage = "scripting"
    update_agent_ui_status("creative", "running", "Generating promotional scripts...")

    with st.spinner("✍️ Agent 2 is writing promotional scripts..."):
        def creative_callback(msg):
            update_agent_ui_status("creative", "running", msg)

        scripts = orchestrator.run_creative(trend_report, status_callback=creative_callback)
        st.session_state.scripts = scripts
        if scripts:
            st.session_state.edited_script = scripts[0].get("full_script", "")
        update_agent_ui_status("creative", "completed", f"Generated {len(scripts)} script variants")

    st.session_state.pipeline_stage = "editing"
    update_agent_ui_status("ui", "active", "Awaiting human review...")


def run_video_generation():
    """Execute Agent 4: Video generation."""
    orchestrator = st.session_state.orchestrator
    st.session_state.pipeline_stage = "generating"
    update_agent_ui_status("video", "running", "Starting video generation...")

    prompt = st.session_state.edited_script
    image_path = st.session_state.uploaded_image_path
    video_settings = st.session_state.get("video_settings", {})

    with st.spinner("🎬 Agent 4 is generating your promotional video... This may take a few minutes."):
        def video_callback(msg):
            update_agent_ui_status("video", "running", msg)

        result = orchestrator.run_video_producer(
            prompt=prompt,
            image_path=image_path,
            video_settings=video_settings,
            status_callback=video_callback,
        )
        st.session_state.video_result = result

    if result and result.get("status") == "completed":
        st.session_state.pipeline_stage = "completed"
        update_agent_ui_status("video", "completed", "Video ready for download!")
    else:
        update_agent_ui_status("video", "error", "Generation failed — check API key and try again")


# ══════════════════════════════════════════════════════════════════════════════
# Environment Status
# ══════════════════════════════════════════════════════════════════════════════
def render_env_status():
    """Show API key status in sidebar."""
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        st.markdown("---")

        if MUAPI_API_KEY:
            st.success("✅ MUAPI_API_KEY configured")
        else:
            st.warning("⚠️ MUAPI_API_KEY not set")
            st.caption("Set in `.env` file for video generation")

        if GEMINI_API_KEY:
            st.success("✅ GEMINI_API_KEY configured")
        else:
            st.info("ℹ️ GEMINI_API_KEY not set")
            st.caption("Will use built-in script templates")

        st.markdown("---")
        st.markdown("### 📁 Artifacts")
        artifact_files = os.listdir(ARTIFACTS_DIR) if os.path.exists(ARTIFACTS_DIR) else []
        if artifact_files:
            for f in artifact_files:
                if f != ".gitkeep":
                    st.caption(f"📄 {f}")
        else:
            st.caption("No artifacts yet")

        st.markdown("---")
        st.markdown(
            "<p style='font-size:0.7rem;color:#666;text-align:center;'>"
            "Built with ❤️ for Vedantu<br>Multi-Agent Marketing System v1.0"
            "</p>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Main Application
# ══════════════════════════════════════════════════════════════════════════════
def main():
    inject_css()
    init_session_state()
    render_env_status()
    render_header()

    # ── Agent Status Panel ────────────────────────────────────────────────
    render_agent_status_panel()

    # ── Status Log ────────────────────────────────────────────────────────
    render_status_log()

    st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)

    # ── Stage: Ready — Start Button ───────────────────────────────────────
    if st.session_state.pipeline_stage == "ready":
        st.markdown("""
        <div class="section-panel" style="text-align:center;">
            <div class="section-title" style="justify-content:center;">
                <span class="icon">🚀</span> Ready to Launch
            </div>
            <p style="color:#a0a0b0;margin-bottom:1rem;">
                Click below to start the multi-agent pipeline. Agent 1 will scrape trending educational topics,
                then Agent 2 will generate promotional scripts for Vedantu.
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Start Agent Pipeline", use_container_width=True, key="start_pipeline"):
                run_scraping_pipeline()
                st.rerun()

    # ── Stage: Editing — Show trends + scripts + HITL ─────────────────────
    elif st.session_state.pipeline_stage in ["editing", "generating", "completed"]:
        # Trend Report
        render_trend_report()

        st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)

        # Script Editor (HITL)
        render_script_editor()

        # Generate Video Button
        if st.session_state.pipeline_stage == "editing":
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                can_generate = bool(MUAPI_API_KEY)
                btn_label = "🎬 Generate Video" if can_generate else "🎬 Generate Video (Set MUAPI_API_KEY first)"
                if st.button(btn_label, use_container_width=True, key="generate_video", disabled=not can_generate):
                    run_video_generation()
                    st.rerun()

                if not can_generate:
                    st.caption("💡 Add your MUAPI_API_KEY to the `.env` file to enable video generation.")

        # Video Result
        if st.session_state.pipeline_stage == "completed":
            st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)
            render_video_result()

    # ── Restart Button ────────────────────────────────────────────────────
    if st.session_state.pipeline_stage != "ready":
        st.markdown("")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("🔄 Restart Pipeline", use_container_width=True, key="restart"):
                for key in ["trend_report", "scripts", "edited_script", "video_result",
                           "uploaded_image_path", "status_log"]:
                    if key in st.session_state:
                        if key == "status_log":
                            st.session_state[key] = []
                        elif key == "edited_script":
                            st.session_state[key] = ""
                        else:
                            st.session_state[key] = None
                st.session_state.pipeline_stage = "ready"
                st.session_state.selected_script_idx = 0
                st.session_state.orchestrator = AgentOrchestrator()
                init_session_state()
                st.rerun()


if __name__ == "__main__":
    main()
