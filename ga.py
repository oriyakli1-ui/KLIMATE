"""Google Analytics 4 helpers: load gtag once and send custom events."""
from __future__ import annotations

import json
import os
import time
import streamlit as st
import streamlit.components.v1 as components


def inject_ga() -> None:
    if os.environ.get("KLIMATE_GA_DISABLED"):
        # Local development: don't pollute production analytics. Events queued by
        # `flush_ga_events` still land in window.dataLayer, so they can be inspected.
        return
    GA_ID = "G-832QG3WMD9"
    ga_js = f"""
    <script>
        // Streamlit reruns this on every interaction; inject only once per page load,
        // otherwise every rerun adds another gtag config (duplicate page_view hits).
        if (!window.parent.document.getElementById('klimate-ga-loader')) {{
            // Inject the gtag.js script
            var script = window.parent.document.createElement('script');
            script.id = 'klimate-ga-loader';
            script.async = true;
            script.src = 'https://www.googletagmanager.com/gtag/js?id={GA_ID}';
            window.parent.document.head.appendChild(script);

            // Inject the configuration script
            var script2 = window.parent.document.createElement('script');
            script2.innerHTML = `
              window.dataLayer = window.dataLayer || [];
              function gtag(){{dataLayer.push(arguments);}}
              gtag('js', new Date());
              gtag('config', '{GA_ID}');
            `;
            window.parent.document.head.appendChild(script2);
        }}
    </script>
    """
    components.html(ga_js, width=0, height=0)


def queue_event(name: str, **params) -> None:
    """Queue a custom GA4 event; it is sent by `flush_ga_events` (this run or the next)."""
    st.session_state.setdefault("_ga_queue", []).append((name, params))


def flush_ga_events() -> None:
    """Send queued GA4 events through the parent page's gtag (fire-and-forget).

    Events are queued rather than sent inline so that ones raised right before
    ``st.rerun()`` are not lost, and each flush gets a unique nonce so Streamlit
    re-executes the script instead of reusing an identical earlier component.
    """
    queue = st.session_state.get("_ga_queue")
    if not queue:
        return
    st.session_state["_ga_queue"] = []

    calls = "\n".join(
        f"w.gtag('event', {json.dumps(name)}, {json.dumps(params)});" for name, params in queue
    )
    components.html(
        f"""
        <script>
        // nonce: {time.time_ns()}
        (function () {{
            try {{
                var w = window.parent;
                w.dataLayer = w.dataLayer || [];
                w.gtag = w.gtag || function () {{ w.dataLayer.push(arguments); }};
                {calls}
            }} catch (e) {{}}
        }})();
        </script>
        """,
        width=0,
        height=0,
    )
