"""Catppuccin Mocha palette for the dashboard.

Applied per-page (inside the ``@ui.page`` builder) so every client gets the dark
theme. :func:`apply_catppuccin_mocha` maps Quasar's semantic colour slots to the
palette and exposes the raw swatches as ``--ctp-*`` CSS variables; panels reference
those variables via :data:`PANEL_STYLE` rather than Tailwind arbitrary-value classes
(which depend on a JIT step we don't want to rely on).

Palette: https://github.com/catppuccin/catppuccin
"""
from nicegui import ui

BASE = "#1e1e2e"
MANTLE = "#181825"
CRUST = "#11111b"
SURFACE0 = "#313244"
SURFACE1 = "#45475a"
TEXT = "#cdd6f4"
SUBTEXT = "#a6adc8"
MAUVE = "#cba6f7"
BLUE = "#89b4fa"
PINK = "#f5c2e7"
GREEN = "#a6e3a1"
RED = "#f38ba8"
YELLOW = "#f9e2af"
TEAL = "#94e2d5"

#: Inline style for a panel card. Inline (not Tailwind `bg-[...]`) so it renders
#: identically regardless of which utility classes NiceGUI's bundle ships with.
PANEL_STYLE = (
    f"background:{SURFACE0};color:{TEXT};border-radius:0.75rem;"
    "box-shadow:0 4px 14px rgba(0,0,0,0.35);overflow:hidden;"
)


def apply_catppuccin_mocha() -> None:
    """Set Quasar colours, force dark mode, and paint the page in Mocha."""
    ui.colors(
        primary=MAUVE, secondary=BLUE, accent=PINK,
        dark=BASE, dark_page=MANTLE,
        positive=GREEN, negative=RED, warning=YELLOW, info=TEAL,
    )
    ui.dark_mode(True)
    ui.add_css(f"""
      :root {{
        --ctp-base:{BASE}; --ctp-mantle:{MANTLE}; --ctp-crust:{CRUST};
        --ctp-surface0:{SURFACE0}; --ctp-surface1:{SURFACE1};
        --ctp-text:{TEXT}; --ctp-subtext:{SUBTEXT};
        --ctp-mauve:{MAUVE}; --ctp-blue:{BLUE}; --ctp-pink:{PINK};
        --ctp-green:{GREEN}; --ctp-red:{RED}; --ctp-yellow:{YELLOW}; --ctp-teal:{TEAL};
      }}
      body, .q-page, .nicegui-content {{
        background: var(--ctp-base); color: var(--ctp-text);
      }}
    """)
