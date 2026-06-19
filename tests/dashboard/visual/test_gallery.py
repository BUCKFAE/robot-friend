"""Tier 2 — screenshot gallery (requirement #1: "look at screenshots … various
aspect ratios").

Renders the scenario × viewport matrix and writes full-page PNGs to
``gallery/<scenario>__<viewport>.png``. A human (or Claude, via the Read tool) opens
the PNGs to eyeball overlap / clipping / contrast. Regenerate the whole set with
``just gallery``. Output is gitignored.
"""
from pathlib import Path

import pytest

GALLERY_DIR = Path(__file__).parent / "gallery"


@pytest.mark.visual
def test_gallery(scenario_server, sized_page, shoot, request):
    scenario, url = scenario_server
    viewport = request.node.viewport_name
    page = sized_page
    page.goto(url, wait_until="domcontentloaded")
    shoot(page, GALLERY_DIR / f"{scenario}__{viewport}.png")
