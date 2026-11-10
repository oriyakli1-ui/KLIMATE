"""seo.py: structured data must stay valid JSON and the injector must not crash."""
from __future__ import annotations

import json

import seo


def test_structured_data_is_valid_json_ld():
    payload = json.dumps(seo.STRUCTURED_DATA)
    parsed = json.loads(payload)
    assert parsed["@type"] == "SoftwareApplication"
    assert parsed["url"] == seo.SITE_URL
    assert parsed["offers"]["price"] == "0"


def test_title_and_description_are_nonempty_plain_text():
    assert seo.TITLE.strip()
    assert seo.DESCRIPTION.strip()
    assert "<" not in seo.TITLE and ">" not in seo.TITLE
    assert "<" not in seo.DESCRIPTION and ">" not in seo.DESCRIPTION


def test_inject_seo_runs_without_error():
    # components.html just renders a stub outside a real Streamlit run; this
    # only guards against f-string/JSON formatting mistakes raising at import/call time.
    seo.inject_seo()
