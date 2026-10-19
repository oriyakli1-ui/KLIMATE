"""Engine Deep Dive page."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import chess
import chess.svg
import chess.pgn
import analysis
import analytics


def format_game_label(row) -> str:
    """Create a compact label for a game row."""
    white = str(row.get("white_player", "White"))
    black = str(row.get("black_player", "Black"))
    result = str(row.get("white_result", "") or row.get("result", "")).strip()
    tc = str(row.get("time_class", "")).strip()
    parts = [f"{white} vs {black}"]
    if tc:
        parts.append(tc)
    if result:
        parts.append(result)
    return " | ".join(parts)


def render_engine_deep_dive(games_df, username: str) -> None:
    """Engine Deep Dive: External cloud eval + visual coaching."""
    st.markdown("### Engine Deep Dive")

    if games_df is None or getattr(games_df, "empty", True):
        st.info("No games available to analyze yet.")
        return
    if "pgn" not in games_df.columns:
        st.info("This dataset doesn't include PGNs, so engine analysis is unavailable.")
        return

    df = games_df.copy().reset_index(drop=True)
    df["label"] = df.apply(format_game_label, axis=1)

    options = list(range(len(df)))
    selected_idx = st.selectbox(
        "Select a game",
        options,
        format_func=lambda i: df.loc[i, "label"],
        key="engine_deep_dive_game_idx",
    )

    selected_pgn = df.loc[selected_idx, "pgn"]
    if not isinstance(selected_pgn, str) or not selected_pgn.strip():
        st.warning("Selected game has no PGN to analyze.")
        return

    if st.button("Analyze Game", width="stretch"):
        st.session_state["analyzed_pgn"] = selected_pgn

    # Persist UI across reruns (e.g., selectbox changes)
    if st.session_state.get("analyzed_pgn") != selected_pgn:
        return

    with st.spinner("It could take a moment, but it's worth it ⏳"):
        eval_df = analytics.analyze_game(selected_pgn)

    if eval_df.empty or "evaluation" not in eval_df.columns:
        st.info("No evaluation data returned for this game (yet).")
        return

    engine_name = str(eval_df["source"].iloc[0]) if "source" in eval_df.columns else "engine"
    missing = int(pd.to_numeric(eval_df["evaluation"], errors="coerce").isna().sum())
    st.caption(f"Analyzed {len(eval_df)} half-moves with {engine_name}.")
    if missing:
        st.warning(
            f"{missing} position(s) could not be evaluated (the analysis service did not answer). "
            "They are left blank in the chart instead of guessed."
        )

    # Accuracy and move quality for both players (Lichess-style win-chance model).
    row = df.loc[selected_idx]
    acc_cols = st.columns(2)
    for col, player in zip(acc_cols, (str(row["white_player"]), str(row["black_player"]))):
        moves = analysis.classify_game(eval_df, selected_pgn, player)
        if moves.empty:
            continue
        counts = analysis.label_counts(moves)
        col.metric(
            f"{player} · accuracy",
            f"{analysis.game_accuracy(moves):.0f}%",
            help="Mean per-move accuracy from the win chance each move gave away (an approximation of Lichess's metric).",
        )
        col.caption(f"{counts['blunder']} blunders · {counts['mistake']} mistakes · {counts['inaccuracy']} inaccuracies")

    # Golden Chart: area eval + blunder markers
    eval_plot = eval_df.copy()
    eval_plot["evaluation"] = pd.to_numeric(eval_plot["evaluation"], errors="coerce")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=eval_plot["ply"],
            y=eval_plot["evaluation"],
            mode="lines",
            connectgaps=False,
            fill="tozeroy",
            name="Evaluation",
            line=dict(color="#06B6D4", width=2),
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(229,231,235,0.35)")

    blunders = analytics.get_all_blunders(eval_df, selected_pgn, username)
    if blunders:
        blunder_plies = [b.get("ply") for b in blunders if b.get("ply") is not None]
        blunder_vals = []
        for p in blunder_plies:
            try:
                v = float(eval_plot.loc[eval_plot["ply"] == int(p), "evaluation"].iloc[0])
            except Exception:
                v = 0.0
            blunder_vals.append(v)
        fig.add_trace(
            go.Scatter(
                x=blunder_plies,
                y=blunder_vals,
                mode="markers",
                name="Blunder",
                marker=dict(symbol="x", color="#EF4444", size=12),
            )
        )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB"),
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Ply",
        yaxis_title="Evaluation (pawns)",
    )

    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    # Blunder Explorer
    if not blunders:
        st.info("No blunders detected yet — try analyzing more plies or a different game.")
        return

    blunders_list = list(blunders)
    selected_idx = st.selectbox(
        "🔍 Select a Key Moment (Mistakes & Blunders):",
        options=list(range(len(blunders_list))),
        format_func=lambda i: f"Move {(int(blunders_list[i].get('ply', 0)) + 1)//2} - Swing: {float(blunders_list[i].get('eval_swing', 0.0)):.2f} pawns",
        key="blunder_explorer_select",
    )

    b = blunders_list[int(selected_idx)]
    ply = int(b.get("ply", 0) or 0)
    move_number = (ply + 1) // 2 if ply > 0 else 0
    color_to_move = "White" if ply % 2 != 0 else "Black"
    eval_swing = float(b.get("eval_swing", 0.0) or 0.0)
    critical_fen = str(b.get("critical_fen", "") or "").strip()
    actual_san = str(b.get("actual_san", "") or "").strip()

    col1, col2 = st.columns([1, 3])
    with col1:
        if not critical_fen:
            st.info("No board position available for this blunder.")
        else:
            try:
                arrows = []
                try:
                    if b.get("actual_move_uci"):
                        m1 = chess.Move.from_uci(b["actual_move_uci"])
                        arrows.append(
                            chess.svg.Arrow(
                                m1.from_square, m1.to_square, color="#EF4444"
                            )
                        )  # RED ARROW
                    if b.get("best_move_uci"):
                        m2 = chess.Move.from_uci(b["best_move_uci"])
                        arrows.append(
                            chess.svg.Arrow(
                                m2.from_square, m2.to_square, color="#10B981"
                            )
                        )  # GREEN ARROW
                except ValueError:
                    pass

                # Orient board to the user's side (since blunders are filtered to user's moves).
                board_orientation = chess.WHITE if (ply % 2 != 0) else chess.BLACK
                svg_data = chess.svg.board(
                    board=chess.Board(b["critical_fen"]),
                    arrows=arrows,
                    orientation=board_orientation,
                    size=350,
                )
                st.write(svg_data, unsafe_allow_html=True)
            except Exception:
                st.info("Failed to render this blunder board.")

    with col2:
        actual = b.get("actual_san") or b.get("actual_move_uci") or "Unknown"
        best = b.get("best_move_san") or b.get("best_move_uci") or "Unknown"

        with st.spinner("🤖 AI Coach is analyzing the position..."):
            explanation = analytics.get_gemini_coach_explanation(
                b["critical_fen"], actual, best, eval_swing
            )
        st.info(f"**🤖 Your AI Coach:**\n\n{explanation}")
