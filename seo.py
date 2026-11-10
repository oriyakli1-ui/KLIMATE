"""SEO + GEO (generative-engine optimization) tags for the single-page Streamlit app.

Streamlit serves one static HTML shell and renders everything client-side, so
there is no per-page <head> to edit at request time. We inject <title>, meta
tags, Open Graph/Twitter cards and JSON-LD structured data into the parent
document once per browser session, the same way ga.inject_ga() injects gtag.

JSON-LD is aimed at LLM answer engines (ChatGPT/Perplexity/Gemini) as much as
classic search: a plain-language description plus a SoftwareApplication
schema gives them something concrete and quotable to cite.
"""
from __future__ import annotations

import json
import streamlit.components.v1 as components

SITE_URL = "https://klimate.streamlit.app/"
OG_IMAGE = SITE_URL.rstrip("/") + "/app/static/logo.png"

TITLE = "Klimate — Chess Psychology Analytics"
DESCRIPTION = (
    "Klimate analyzes your Chess.com or Lichess games to find the habits that "
    "actually cost you rating points: tilt, late-night play, time scrambles and "
    "repeated opening mistakes. Free, reads public games only, nothing is stored."
)
KEYWORDS = (
    "chess analytics, chess psychology, chess tilt, chess rating analysis, "
    "chess.com stats, lichess stats, chess improvement tool, chess coach AI, "
    "chess blunder finder, chess opening analysis"
)

STRUCTURED_DATA = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "Klimate",
    "applicationCategory": "SportsApplication",
    "operatingSystem": "Any (web browser)",
    "url": SITE_URL,
    "description": DESCRIPTION,
    "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
    "featureList": [
        "Tilt and session-aware performance analysis",
        "Time-management and clock-scramble detection",
        "Opening-by-opening engine evaluation",
        "Stockfish-powered coach report",
        "Elo Ledger: rating points gained or lost per habit",
        "Blunder trainer built from your own missed moves",
    ],
}


def inject_seo() -> None:
    """Inject <title>, meta tags, Open Graph/Twitter cards and JSON-LD once per load."""
    payload = json.dumps(STRUCTURED_DATA)
    seo_js = f"""
    <script>
        (function() {{
            var doc = window.parent.document;
            if (doc.getElementById('klimate-seo-loader')) {{ return; }}
            var marker = doc.createElement('meta');
            marker.id = 'klimate-seo-loader';
            marker.name = 'klimate-seo-loader';
            doc.head.appendChild(marker);

            doc.title = {json.dumps(TITLE)};

            function setMeta(attr, key, content) {{
                var el = doc.querySelector('meta[' + attr + '="' + key + '"]');
                if (!el) {{
                    el = doc.createElement('meta');
                    el.setAttribute(attr, key);
                    doc.head.appendChild(el);
                }}
                el.setAttribute('content', content);
            }}

            setMeta('name', 'description', {json.dumps(DESCRIPTION)});
            setMeta('name', 'keywords', {json.dumps(KEYWORDS)});
            setMeta('name', 'robots', 'index, follow');
            setMeta('property', 'og:type', 'website');
            setMeta('property', 'og:title', {json.dumps(TITLE)});
            setMeta('property', 'og:description', {json.dumps(DESCRIPTION)});
            setMeta('property', 'og:url', {json.dumps(SITE_URL)});
            setMeta('property', 'og:image', {json.dumps(OG_IMAGE)});
            setMeta('name', 'twitter:card', 'summary_large_image');
            setMeta('name', 'twitter:title', {json.dumps(TITLE)});
            setMeta('name', 'twitter:description', {json.dumps(DESCRIPTION)});
            setMeta('name', 'twitter:image', {json.dumps(OG_IMAGE)});

            var canonical = doc.querySelector('link[rel="canonical"]');
            if (!canonical) {{
                canonical = doc.createElement('link');
                canonical.setAttribute('rel', 'canonical');
                doc.head.appendChild(canonical);
            }}
            canonical.setAttribute('href', {json.dumps(SITE_URL)});

            var ld = doc.createElement('script');
            ld.type = 'application/ld+json';
            ld.id = 'klimate-ld-json';
            ld.text = {json.dumps(payload)};
            doc.head.appendChild(ld);
        }})();
    </script>
    """
    components.html(seo_js, width=0, height=0)
