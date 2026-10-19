"""Streamlit pages built on insights.py (behaviour lab, time management, insight cards)."""
from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import insights
from i18n import he_losses, insight_text, t

CYAN, GREEN, RED, GREY = "#06B6D4", "#10B981", "#EF4444", "#64748B"


def _bar(x, y, title: str, labels, baseline: float | None = None, colors=None, height: int = 320, pct: bool = True):
    fig = go.Figure(
        go.Bar(
            x=x,
            y=y,
            text=labels,
            textposition="outside",
            marker_color=colors or CYAN,
            cliponaxis=False,
        )
    )
    if baseline is not None and baseline == baseline:
        fig.add_hline(
            y=baseline,
            line_dash="dash",
            line_color="rgba(229,231,235,0.5)",
            annotation_text=f"overall {baseline:.0%}",
            annotation_font_color="#E5E7EB",
        )
    fig.update_layout(
        title=dict(text=title, font=dict(color="#F8FAFC", size=16)),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB"),
        height=height,
        margin=dict(l=20, r=20, t=50, b=20),
        # category axis: labels like "0", "1", "3+" must not be read as numbers
        xaxis=dict(type="category"),
        yaxis=(dict(range=[0, 1], tickformat=".0%", gridcolor="rgba(148,163,184,0.2)") if pct
               else dict(rangemode="tozero", gridcolor="rgba(148,163,184,0.2)")),
    )
    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


def _card(title: str, detail: str, tone: str = "warn", link: str = "", link_text: str = "open the exercise") -> None:
    """Callout card. Text is HTML-escaped (it may contain data-derived names); ``link`` becomes an anchor."""
    accent = {"warn": "#F59E0B", "good": GREEN, "info": CYAN}[tone]
    anchor = (
        f" · <a href=\"{html.escape(link, quote=True)}\" target=\"_blank\" rel=\"noopener noreferrer\" "
        f"style=\"color:{CYAN};\">{html.escape(link_text)}</a>"
        if link else ""
    )
    st.markdown(
        f"<div style='background:#1E293B;border-left:4px solid {accent};border-radius:10px;"
        f"padding:0.9rem 1.1rem;margin:0.5rem 0;'>"
        f"<div style='font-weight:700;color:#F8FAFC;'>{html.escape(title)}</div>"
        f"<div style='color:#CBD5E1;margin-top:0.25rem;'>{html.escape(detail)}{anchor}</div></div>",
        unsafe_allow_html=True,
    )


def render_insights_panel(g: pd.DataFrame) -> None:
    """Top findings that are statistically backed, or an honest 'nothing reliable yet'."""
    st.markdown("### " + t("insights_title"))
    if len(g) < 20:
        st.info(t("min_games"))
        return
    found = insights.generate_insights(g)
    if not found:
        _card(
            t("no_pattern_title"),
            t("no_pattern_detail", n=len(g)),
            "info",
        )
        return
    for f in found[:3]:
        txt = insight_text(f)
        _card(txt["title"], txt["detail"])
    if len(found) > 3:
        with st.expander(t("more_insights", n=len(found) - 3)):
            for f in found[3:]:
                txt = insight_text(f)
                _card(txt["title"], txt["detail"])
    st.caption(t("insights_caption"))


def render_behavior_lab(g: pd.DataFrame) -> None:
    st.markdown("### " + t("behavior_title"))
    if len(g) < 20:
        st.info(t("min_games"))
        return

    sp = insights.session_profile(g)
    tp = insights.tilt_profile(g)
    cols = st.columns(4)
    cols[0].metric(t("sessions"), sp["sessions"])
    cols[1].metric(t("games_session"), f"{sp['avg_games']:.1f}")
    cols[2].metric(t("longest_session"), sp["longest"])
    cols[3].metric(t("overall_score"), f"{tp['baseline']:.0%}")
    st.caption(t("session_caption", m=insights.SESSION_GAP_MINUTES))

    st.markdown("#### " + t("tilt_header"))
    tilt_table = tp["table"]
    _bar(
        tilt_table["bucket"], tilt_table["score"], t("tilt_chart"),
        [f"{s:.0%}<br>n={n}" for s, n in zip(tilt_table["score"], tilt_table["games"])], baseline=tp["baseline"],
        colors=[GREEN if b == "0" else RED for b in tilt_table["bucket"]],
    )
    if tp["stop_loss_after"]:
        _card(
            t("stop_card_title", n=tp["stop_loss_after"], es="es" if tp["stop_loss_after"] > 1 else "", n_he=he_losses(int(tp["stop_loss_after"]))),
            t("stop_card_detail"),
        )
    elif tp["enough_data"]:
        _card(t("no_tilt_title"), t("no_tilt_detail"), "good")
    else:
        st.info("Too few games after losses to judge tilt yet.")

    st.markdown("#### " + t("warmup_header"))
    s = sp["by_game_no"]
    _bar(s["bucket"], s["score"], t("warmup_chart"),
         [f"{v:.0%}<br>n={n}" for v, n in zip(s["score"], s["games"])], baseline=tp["baseline"])

    st.markdown("#### " + t("opp_header"))
    gap = insights.rating_gap_profile(g)
    if not gap.empty:
        _bar(gap["band"].astype(str), gap["score"], t("opp_chart"),
             [f"{v:.0%}<br>n={n}" for v, n in zip(gap["score"], gap["games"])], baseline=tp["baseline"])

    st.markdown("#### " + t("colour_header"))
    col = insights.color_profile(g)
    if not col.empty:
        _bar([c.title() for c in col["user_color"]], col["score"], t("colour_chart"),
             [f"{v:.0%}<br>n={n}" for v, n in zip(col["score"], col["games"])], baseline=tp["baseline"],
             colors=["#E2E8F0" if c == "white" else GREY for c in col["user_color"]], height=280)


def render_time_management(g: pd.DataFrame) -> None:
    st.markdown("### " + t("time_title"))
    cp = insights.clock_profile(g)
    if not cp:
        st.info("This needs games with clock data (Chess.com live games). " + t("min_games"))
        return

    c = st.columns(4)
    c[0].metric(t("games_clocks"), cp["games"])
    c[1].metric(t("scramble_rate"), f"{cp['scramble_rate']:.0%}", help="Games that end with under ~10% of the starting time (min 10s, max 30s).")
    c[2].metric(t("timeouts_wl"), f"{cp['timeout_losses']} / {cp['timeout_wins']}")
    med = cp["median_clock_after_15_pct"]
    c[3].metric(t("clock_15"), f"{med:.0%}" if med == med else "n/a", help="Median share of your starting time still on the clock after your 15th move.")

    labels, vals, ns = [], [], []
    for name, key, n_key in (("No scramble", "no_scramble_score", None), ("Scramble", "scramble_score", "scramble_n"),
                             ("≥70% clock left at move 15", "calm_score", "calm_n"), ("<70% clock left at move 15", "burn_score", "burn_n")):
        v = cp[key]
        if v == v:
            labels.append(name)
            vals.append(v)
            ns.append(cp[n_key] if n_key else cp["games"] - cp["scramble_n"])
    _bar(labels, vals, t("clock_chart"), [f"{v:.0%}<br>n={n}" for v, n in zip(vals, ns)],
         colors=[GREEN, RED, GREEN, RED][: len(vals)] if len(vals) == 4 else CYAN)

    d = g[g["avg_move_seconds"].notna()]
    if not d.empty:
        by_tc = (
            d.groupby("time_class")
            .agg(games=("score", "size"), avg_move=("avg_move_seconds", "mean"), final_clock=("final_clock", "median"))
            .round(1)
            .reset_index()
        )
        by_tc.columns = ["Time class", "Games", "Avg seconds per move", "Median clock left at the end (s)"]
        st.markdown("#### " + t("by_time_class"))
        st.dataframe(by_tc, hide_index=True, width="stretch")
