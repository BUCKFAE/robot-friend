"""Draggable/resizable dashboard grid, backed by Gridstack.js.

Rather than NiceGUI's custom-Vue-component path (an ``esm=`` import map + resource
bundling — version-specific and awkward), we load vendored Gridstack as a global lib
and build the grid from plain NiceGUI elements: a ``.grid-stack`` container whose
children are ``.grid-stack-item > .grid-stack-item-content`` wrappers around each
panel. :data:`GRIDSTACK_INIT_JS` calls ``GridStack.init()`` once those elements exist
(NiceGUI renders the tree client-side over a websocket, so we poll), then:

* **persists** the layout per-device to ``localStorage`` on every change and restores
  it on load (tiles carry a stable ``gs-id``);
* limits resizing to the bottom-right corner and hides the grip, so there's no stray
  resize button (the bottom-left grip Gridstack adds by default looked misplaced).

:data:`GRIDSTACK_RESET_JS` clears the saved layout and reloads (wired to a button).

Usage::

    grid = GridContainer()
    grid.add(lambda: VideoPanel(bus, streams, "raw", title="Raw"), w=6, h=5, x=0, y=0, item_id="raw")
"""
from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from robot_friend.resource_handler import (
    get_dashboard_static_dir,
    get_dashboard_static_file,
)

_STATIC_DIR = get_dashboard_static_dir()
_STATIC_URL = "/dashboard/static"

#: <head> tags: Gridstack stylesheet + library, plus a style that removes the visible
#: resize grip (resizing still works by dragging the bottom-right corner).
GRIDSTACK_HEAD_HTML = get_dashboard_static_file("gridstack_head.html").read_text()

#: DOM-ready initialiser: poll until the library + container + items exist, init once,
#: restore any saved per-device layout, then persist on every change. ``float: true`` is
#: intentional — tiles stay exactly where placed (free space stays free; no auto-gravity).
GRIDSTACK_INIT_JS = get_dashboard_static_file("gridstack_init.html").read_text()

#: JS the "Reset layout" button runs: forget the saved layout and reload to defaults.
GRIDSTACK_RESET_JS = get_dashboard_static_file("gridstack-reset.js").read_text()


def mount_gridstack_static(app) -> None:
    """Serve the vendored Gridstack assets (call once, at import, before ui.run)."""
    app.add_static_files(_STATIC_URL, str(_STATIC_DIR))


class GridContainer(ui.element):
    def __init__(self) -> None:
        super().__init__("div")
        self.classes("grid-stack").style("width:100%")

    def add(self, factory: Callable[[], object], *, w: int = 4, h: int = 4,
            x: int | None = None, y: int | None = None, item_id: str | None = None) -> "GridContainer":
        """Add a panel built by ``factory`` as a grid tile of ``w``×``h`` cells
        (optionally placed at ``x``,``y``). ``item_id`` is a stable id so saved layouts
        restore to the right tile. The panel renders inside the
        ``.grid-stack-item-content`` wrapper Gridstack manages."""
        with self:
            item = ui.element("div").classes("grid-stack-item").props(f"gs-w={w} gs-h={h}")
            if x is not None:
                item.props(f"gs-x={x}")
            if y is not None:
                item.props(f"gs-y={y}")
            if item_id is not None:
                item.props(f"gs-id={item_id}")
            with item, ui.element("div").classes("grid-stack-item-content"):
                factory()
        return self
