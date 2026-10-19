"""Engine Deep Dive page: analyze one game and study its key mistakes."""
from __future__ import annotations

import chess
import chess.pgn
import chess.svg
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analysis
import analytics

LABEL_COLOURS = {"blunder": "#EF4444", "mistake": "#F59E0B"}


def format_game_label(row, username: str) -> str:
    """'2026-10-19 · rapid · vs opponent · loss' from the selected player's point of view."""
    me = username.strip().lower()
    white = str(row.get("white_player", "")).strip().lower() == me
    opp = row.get("black_player") if white else row.get("white_player")
    mine = str(row.get("white_result") if white else row.get("black_result"))
    theirs = str(row.get("black_result") if white else row.get("white_result"))
    outcome = "win" if mine == "win" else ("loss" if theirs == "win" else "draw")
    date = pd.to_datetime(row.get("date_utc"), utc=True).strftime("%Y-%m-%d") if row.get("date_utc") is not None else ""
    return f"{date} · {row.get('time_class', '')} · vs {opp} · {outcome}"


def render_engine_deep_dive(games_df, username: str) -> None:
    st.markdown("### Engine Deep Dive")
    if games_df is None or getattr(games_df, "empty", True):
        st.info("No games available to analyze yet.")
        return
    if "pgn" not in games_df.columns:
        st.info("This dataset doesn't include PGNs, so engine analysis is unavailable.")
        return

    df = games_df.copy().reset_index(drop=True)
    labels = [format_game_label(r, username) for _, r in df.iterrows()]
    selected_idx = st.selectbox("Select a game", list(range(len(df))), format_func=lambda i: labels[i], key="engine_deep_dive_game_idx")

    selected_pgn = df.loc[selected_idx, "pgn"]
    if not isinstance(selected_pgn, str) or not selected_pgn.strip():
        st.warning("Selected game has no PGN to analyze.")
        return
    if st.button("Analyze Game", width="stretch"):
        st.session_state["analyzed_pgn"] = selected_pgn
    if st.session_state.get("analyzed_pgn") != selected_pgn:  # keep the result across reruns
        return

    with st.spinner("Analyzing…"):
        eval_df = analytics.analyze_game(selected_pgn)
    if eval_df.empty or "evaluation" not in eval_df.columns:
        st.info("No evaluation data returned for this game (yet).")
        return

    engine_name = str(eval_df["source"].iloc[0]) if "source" in eval_df.columns else "engine"
    total_plies = int(df.loc[selected_idx, "plies"]) if "plies" in df.columns else len(eval_df)
    st.caption(f"Analyzed {len(eval_df)} of {total_plies} half-moves with {engine_name}.")
    if len(eval_df) < total_plies:
        st.warning("Only the first part of the game was analyzed (the web fallback is limited). Accuracy covers those moves only.")
    missing = int(pd.to_numeric(eval_df["evaluation"], errors="coerce").isna().sum())
    if missing:
        st.warning(f"{missing} position(s) could not be evaluated. They are left blank instead of guessed.")

    st.caption("Labels use the win chance a move gives away: inaccuracy 10+ points, mistake 20+, blunder 30+ "
               "(a convention inspired by Lichess). Evaluations come from Stockfish at a fixed depth, so borderline moves can change with deeper analysis.")
    row = df.loc[selected_idx]
    cols = st.columns(2)
    for col, player in zip(cols, (str(row["white_player"]), str(row["black_player"]))):
        moves = analysis.classify_game(eval_df, selected_pgn, player)
        if moves.empty:
            continue
        counts = analysis.label_counts(moves)
        col.metric(f"{player} · accuracy", f"{analysis.game_accuracy(moves):.0f}%",
                   help="Mean per-move accuracy from the win chance each move gave away (Lichess's per-move formula; the game value is a plain average, so it can differ slightly from Lichess's own).")
        col.caption(f"{counts['blunder']} blunders · {counts['mistake']} mistakes · {counts['inaccuracy']} inaccuracies")

    moments = analysis.key_moments(eval_df, selected_pgn, username)

    fig = go.Figure(go.Scatter(x=eval_df["ply"], y=pd.to_numeric(eval_df["evaluation"], errors="coerce"), mode="lines",
                               connectgaps=False, fill="tozeroy", name="Evaluation", line=dict(color="#06B6D4", width=2)))
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(229,231,235,0.35)")
    for kind, colour in LABEL_COLOURS.items():
        pts = [m for m in moments if m["label"] == kind]
        if pts:
            ev = eval_df.set_index("ply")["evaluation"]
            fig.add_trace(go.Scatter(x=[m["ply"] for m in pts], y=[float(ev.get(m["ply"], 0.0)) for m in pts], mode="markers",
                                     name=f"Your {kind}", marker=dict(symbol="x", color=colour, size=12)))
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#E5E7EB"),
                      margin=dict(l=20, r=20, t=30, b=20), xaxis_title="Half-move", yaxis_title="Evaluation (pawns, White's view)")
    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    if not moments:
        st.info("No mistakes or blunders by you in the analyzed part of this game.")
        return

    pick = st.selectbox(
        "🔍 Key moments (your biggest mistakes)", list(range(len(moments))), key="blunder_explorer_select",
        format_func=lambda i: f"Move {moments[i]['move_number']} · {moments[i]['san']} · {moments[i]['label']} · "
                              f"gave away {moments[i]['win_loss']:.0f}% win chance",
    )
    m = moments[pick]
    user_is_white = str(row["white_player"]).strip().lower() == username.strip().lower()

    col1, col2 = st.columns([1, 2])
    with col1:
        arrows = []
        for uci, colour in ((m["played_uci"], "#EF4444"), (m["best_uci"], "#10B981")):
            if uci:
                mv = chess.Move.from_uci(uci)
                arrows.append(chess.svg.Arrow(mv.from_square, mv.to_square, color=colour))
        st.write(chess.svg.board(board=chess.Board(m["fen"]), arrows=arrows,
                                 orientation=chess.WHITE if user_is_white else chess.BLACK, size=350), unsafe_allow_html=True)
        st.caption("Red: your move. Green: the engine's choice.")
    with col2:
        best = m["best_san"] or "n/a"
        st.markdown(f"**You played {m['san']}** and gave away about **{m['win_loss']:.0f}%** of your winning chances. "
                    f"The engine preferred **{best}**.")
        with st.spinner("🤖 AI Coach is analyzing the position..."):
            explanation = analytics.get_gemini_coach_explanation(m["fen"], m["san"], best, m["win_loss"])
        st.info(f"**🤖 Your AI Coach:**\n\n{explanation}")
