"""The shareable Wrapped card dialog."""
from __future__ import annotations

import datetime
import html
import json

import streamlit as st
import streamlit.components.v1 as components

import analytics
import share_card
import wrapped as wrapped_data
from ga import queue_event


def render_wrapped_card(username: str, ratings: dict, enriched, raw_games, timezone: str) -> None:
    current_date = datetime.datetime.now().strftime("%B %d, %Y")
    wrapped = wrapped_data.build_wrapped(enriched, raw_games, username, ratings, timezone)
    safe = {k: html.escape(str(v)) for k, v in wrapped.items()}
    user_html = html.escape(username.upper())

    # The HTML for the card itself (must have id='klimate-masterpiece-card')
    card_html = f"""
    <div id="klimate-masterpiece-card" class="masterpiece-card" style="position: relative; background: radial-gradient(circle at 50% 0%, #1E293B, #020617 80%); padding: 3rem 2rem; border-radius: 24px; color: white; text-align: center; font-family: sans-serif;">
        <div style="color: #F8FAFC; letter-spacing: 0.2em; font-size: 0.9rem; margin-bottom: 0.5rem; font-weight: 600;">KLIMATE CHESS DNA</div>
        <h1 style="font-size: 3.2rem; margin: 0; background: linear-gradient(90deg, #06B6D4, #10B981); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{user_html}</h1>
        <div style="color: #F8FAFC; font-size: 1.05rem; margin-bottom: 2rem; font-weight: 600;">{current_date}</div>
        
        <div style="background: rgba(15,23,42,0.6); border: 1px solid rgba(16,185,129,0.4); border-radius: 20px; padding: 2rem; margin-bottom: 1.5rem;">
            <div style="font-size: 4rem; font-weight: 900; color: #10B981;">{safe['peak_rating']}</div>
            <div style="color: #F8FAFC; font-size: 0.9rem; letter-spacing: 0.1em; text-transform: uppercase; font-weight: 600;">👑 {safe['peak_label']}</div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div style="background: rgba(255,255,255,0.05); padding: 1.2rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="font-size: 0.8rem; color: #F8FAFC; text-transform: uppercase; font-weight: 600; margin-bottom: 0.3rem;">🏆 Wins</div>
                <div style="font-size: 1.3rem; font-weight: 800; color: white;">{safe['wins']}</div>
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 1.2rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="font-size: 0.8rem; color: #F8FAFC; text-transform: uppercase; font-weight: 600; margin-bottom: 0.3rem;">🗡️ Best Opening</div>
                <div style="font-size: 1.3rem; font-weight: 800; color: white;">{safe['best_opening']}</div>
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 1.2rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="font-size: 0.8rem; color: #F8FAFC; text-transform: uppercase; font-weight: 600; margin-bottom: 0.3rem;">⚡ Prime Time</div>
                <div style="font-size: 1.3rem; font-weight: 800; color: white;">{safe['prime_time']}</div>
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 1.2rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="font-size: 0.8rem; color: #F8FAFC; text-transform: uppercase; font-weight: 600; margin-bottom: 0.3rem;">♟️ Plays Like (for fun)</div>
                <div style="font-size: 1.3rem; font-weight: 800; color: #10B981;">{safe['gm_match']}</div>
            </div>
        </div>
    </div>
    """

    # 1. Define the viral text
    app_url = "https://klimate.streamlit.app/" 
    share_text = f"""🚀 I just analyzed my Chess DNA with Klimate!

👑 {wrapped['peak_label']}: {wrapped['peak_rating']}
🏆 Wins: {wrapped['wins']}
🗡️ Best opening: {wrapped['best_opening']}
⚡ Prime time: {wrapped['prime_time']}
♟️ Plays like (for fun): {wrapped['gm_match']}

Discover your own chess psychology and blind spots: {app_url}

#Klimate #Chess
"""

    js_share_text = json.dumps(share_text)

    # 2. The Copy & Open Script
    share_script = f"""
    <div style="display: flex; justify-content: center; margin-top: 30px; margin-bottom: 20px;">
        <button onclick='shareToLinkedIn()' style="background: linear-gradient(90deg, #0A66C2, #004182); color: white; padding: 14px 28px; border: none; border-radius: 12px; font-weight: 700; font-size: 1.1rem; cursor: pointer; box-shadow: 0 8px 15px rgba(10, 102, 194, 0.4); transition: transform 0.2s; display: flex; align-items: center; gap: 10px;">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>
            Copy Data & Open LinkedIn
        </button>
    </div>

    <script>
    function shareToLinkedIn() {{
        try {{ window.parent.gtag('event', 'wrapped_share_clicked'); }} catch (e) {{}}
        const tempTextArea = document.createElement("textarea");
        tempTextArea.value = {js_share_text};
        document.body.appendChild(tempTextArea);
        tempTextArea.select();
        tempTextArea.setSelectionRange(0, 99999); 
        
        try {{
            document.execCommand("copy");
            const btn = document.querySelector('button');
            const originalText = btn.innerHTML;
            btn.innerHTML = '✅ Copied! Opening LinkedIn...';
            
            setTimeout(() => {{
                window.open('https://www.linkedin.com/feed/', '_blank');
                btn.innerHTML = originalText;
            }}, 1500);
            
        }} catch (err) {{
            console.error('Oops, unable to copy', err);
            alert('Unable to copy automatically. Please copy manually.');
        }}
        
        document.body.removeChild(tempTextArea);
    }}
    </script>
    """

    # Render everything using components.html to ensure JS context is whole
    components.html(card_html + share_script, height=750, scrolling=True)

    st.download_button(
        "⬇️ Download as image",
        data=share_card.render_wrapped_png(username, wrapped),
        file_name=f"klimate-{username}.png",
        mime="image/png",
        on_click=lambda: queue_event("wrapped_downloaded"),
    )


@st.dialog("Your Chess DNA", width="large")
def show_klimate_masterpiece(username: str, enriched, raw_games, timezone: str) -> None:
    render_wrapped_card(username, analytics.get_real_time_ratings(username), enriched, raw_games, timezone)
