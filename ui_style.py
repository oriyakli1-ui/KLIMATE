"""Global CSS for the dark Bento theme."""
from __future__ import annotations

import streamlit as st


def inject_global_styles() -> None:
    """Inject custom CSS for the Slate & Cyan Bento Box dark theme."""
    st.markdown(
        """
        <style>
        /* Global page styling */
        body, .stApp {
            background-color: #0F172A;
            color: #E5E7EB;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }

        /* Global label styling (e.g. filter labels) */
        label {
            color: #F8FAFC !important;
            font-weight: 600;
        }

        /* Hero section */
        .klimate-hero-title {
            font-size: 2.4rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            color: #E5E7EB;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .klimate-hero-subtitle {
            font-size: 1.2rem;
            color: #F8FAFC;
            text-align: center;
            margin-bottom: 1.5rem;
            font-weight: 600;
        }

        /* Bento cards */
        .klimate-card {
            background: #1E293B;
            border-radius: 15px;
            padding: 20px 22px;
            border: 1px solid #334155;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.8);
        }
        .klimate-metric-label {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #F8FAFC;
            margin-bottom: 0.3rem;
            font-weight: 600;
        }
        .klimate-metric-value {
            font-size: clamp(1.4rem, 2.2vw, 1.9rem);
            font-weight: 700;
            color: #E5E7EB;
            white-space: nowrap;
        }
        .klimate-metric-sub {
            color: #94A3B8;
            font-size: 0.8rem;
            margin-top: 0.15rem;
        }
        .klimate-card { min-height: 112px; }

        /* Home hero */
        .klimate-hero { background: radial-gradient(circle at top left, #1E293B, #0B1220); border: 1px solid #334155; border-radius: 16px;
            padding: 1.2rem 1.4rem; margin-bottom: 0.9rem; }
        .klimate-hero .hero-kicker { color: #06B6D4; font-size: 0.78rem; letter-spacing: 0.18em; font-weight: 700; }
        .klimate-hero .hero-title { color: #F8FAFC; font-size: 1.35rem; font-weight: 700; margin-top: 0.25rem; }
        .hero-card { background: #1E293B; border: 1px solid #334155; border-radius: 14px; padding: 1rem 1.1rem; height: 100%; min-height: 150px; margin-bottom: 0.7rem; }
        .hero-card.leak { border-top: 3px solid #F59E0B; }
        .hero-card.strength { border-top: 3px solid #10B981; }
        .hero-card .hc-label { color: #94A3B8; font-size: 0.74rem; letter-spacing: 0.12em; font-weight: 700; }
        .hero-card .hc-value { color: #F8FAFC; font-size: 2.4rem; font-weight: 800; line-height: 1.15; }
        .hero-card .hc-title { color: #F8FAFC; font-size: 1.05rem; font-weight: 700; margin: 0.3rem 0 0.2rem 0; }
        .hero-card .hc-sub { color: #CBD5E1; font-size: 0.9rem; line-height: 1.4; }
        .hero-card .hc-link { color: #06B6D4; font-size: 0.8rem; margin-top: 0.4rem; }

        /* Landing page value cards */
        .klimate-value-card {
            background: #1E293B; border: 1px solid #334155; border-radius: 14px; padding: 1.1rem 1.2rem; height: 100%;
        }
        .klimate-value-card .vc-icon { font-size: 1.5rem; }
        .klimate-value-card .vc-title { color: #F8FAFC; font-weight: 700; margin: 0.3rem 0 0.2rem 0; }
        .klimate-value-card .vc-text { color: #94A3B8; font-size: 0.92rem; line-height: 1.45; }

        /* Dark sidebar so labels, radios and menus are readable whatever theme the browser prefers */
        [data-testid="stSidebar"] { background-color: #0B1220; border-right: 1px solid #1E293B; }
        [data-testid="stSidebar"] * { color: #E5E7EB; }
        [data-testid="stSidebar"] .stButton > button p { color: #0F172A !important; }
        [data-testid="stSidebar"] .stDownloadButton > button { background: #1E293B; border: 1px solid #334155; }
        [data-testid="stSidebar"] .stDownloadButton > button p { color: #E5E7EB !important; }
        [data-testid="stSidebar"] [data-testid="stExpander"] { border: 1px solid #1E293B; border-radius: 10px; }

        /* Metrics: readable values on the dark page */
        [data-testid="stMetricValue"] { color: #F8FAFC !important; }
        [data-testid="stMetricLabel"] p { color: #94A3B8 !important; }

        /* Hide Streamlit's own footer; keep the page clean */
        footer { visibility: hidden; }
        @media (max-width: 768px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
            .klimate-card { padding: 14px 14px; min-height: 96px; }
        }
        .klimate-metric-value--success {
            color: #10B981;
        }
        .klimate-metric-value--danger {
            color: #EF4444;
        }
        .klimate-metric-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 0.95rem;
            font-weight: 600;
            margin-top: 0.4rem;
        }
        .badge-neutral {
            background: rgba(148, 163, 184, 0.16);
            color: #F8FAFC;
        }
        .badge-success {
            background: rgba(16, 185, 129, 0.14);
            color: #F8FAFC;
        }
        .badge-danger {
            background: rgba(239, 68, 68, 0.14);
            color: #F8FAFC;
        }

        /* Input styling */
        .stTextInput > div > div > input {
            background-color: #020617;
            color: #E5E7EB;
            border-radius: 999px;
            border: 1px solid #1F2937;
        }
        .stTextInput > div > div > input:focus {
            border-color: #06B6D4;
            box-shadow: 0 0 0 1px #06B6D4;
        }
        .stButton > button {
            border-radius: 999px;
            background: linear-gradient(90deg, #06B6D4, #10B981);
            color: #0F172A;
            font-weight: 600;
            border: none;
            padding: 0.55rem 1.8rem;
        }
        .stButton > button:hover {
            filter: brightness(1.05);
        }

        /* Plotly card */
        .klimate-card-plot {
            background: #1E293B;
            border-radius: 15px;
            padding: 16px 18px 6px 18px;
            border: 1px solid #334155;
        }

        /* Custom tooltip for metric cards */
        .custom-tooltip {
            position: relative;
            display: inline-block;
            cursor: pointer;
            float: right;
            opacity: 0.7;
            font-size: 16px;
        }
        .custom-tooltip:hover {
            opacity: 1;
        }
        .custom-tooltip .tooltip-text {
            visibility: hidden;
            width: 260px;
            background-color: #1E293B;
            color: #E2E8F0;
            text-align: left;
            border-radius: 8px;
            padding: 12px;
            position: absolute;
            z-index: 999;
            top: 130%;
            right: 0;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 13px;
            font-weight: 400;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5);
            border: 1px solid #334155;
            line-height: 1.5;
        }
        .custom-tooltip:hover .tooltip-text {
            visibility: visible;
            opacity: 1;
        }

        /* Brighter alert/insight text (e.g. Spatial Analysis insights) */
        div[data-testid="stAlert"] {
            color: #F8FAFC !important;
            font-weight: 600;
        }
        div[data-testid="stAlert"] p {
            color: #F8FAFC !important;
            font-weight: 600;
        }

        /* Heatmaps: Label and Title Styling */
        .plotly-graph-div .g-gtitle text,
        .plotly-graph-div .g-axis text,
        .plotly-graph-div .g-legend text {
            fill: #F8FAFC !important; /* very light grey / off-white */
        }

        /* Custom Plotly Tooltip Styling for a modern look (e.g. Opening DNA) */
        .plotly-graph-div .hoverlayer .hovertext rect {
            fill: #1E293B !important;  /* dark Bento background */
            stroke: none !important;   /* no outline */
            rx: 8px !important;        /* rounded corners (x-radius) */
            ry: 8px !important;        /* rounded corners (y-radius) */
        }
        .plotly-graph-div .hoverlayer .hovertext text {
            fill: #F1F5F9 !important;  /* off-white text */
        }

        /* Tabs (Activity Map / Vulnerability Map) */
        .stTabs [role="tab"] {
            color: #F8FAFC !important;
            font-weight: 600;
        }
        .stTabs [role="tab"][aria-selected="true"] {
            border-bottom: 2px solid rgba(16, 185, 129, 0.9);
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.6);
        }

        .masterpiece-card {
            background: radial-gradient(circle at top left, #1E293B, #020617);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-top: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            padding: 2.5rem;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 30px rgba(6, 182, 212, 0.15);
            text-align: center;
            margin-bottom: 2rem;
            color: #F8FAFC;
        }
        .mp-header { color: #F8FAFC; font-size: 1.15rem; letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 0.5rem; font-weight: 600; }
        .mp-username { 
            font-size: 2.8rem; font-weight: 800; margin: 0; 
            background: linear-gradient(90deg, #06B6D4, #10B981);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            text-transform: uppercase;
        }
        .mp-date { color: #F8FAFC; font-size: 1.05rem; margin-bottom: 2rem; font-weight: 600; }
        .mp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; text-align: left; }
        .mp-stat-box { background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.01)); border-radius: 16px; padding: 1.5rem; border: 1px solid rgba(255, 255, 255, 0.08); transition: transform 0.3s ease, box-shadow 0.3s ease; }
        .mp-stat-box:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
            border-color: rgba(6, 182, 212, 0.4);
        }
        .mp-icon { font-size: 1.5rem; margin-bottom: 0.5rem; }
        .mp-label { color: #F8FAFC; font-size: 1.05rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.2rem; font-weight: 600; }
        .mp-value { color: #FFFFFF; font-size: 1.5rem; font-weight: 800; margin-top: 0.3rem; letter-spacing: 0.02em; }
        .mp-footer { margin-top: 2rem; font-size: 1.05rem; color: #F8FAFC; letter-spacing: 0.1em; font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )
