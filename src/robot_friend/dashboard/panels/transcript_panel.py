"""Transcript panel optimized for the live speech stream."""
from __future__ import annotations

from nicegui import ui

from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.panels.panel import Panel, register
from robot_friend.dashboard.sources.dataclass import TRANSCRIPT_CHANNEL
from robot_friend.audio.transcript import Transcript


@register("transcript")
class TranscriptPanel(Panel):
    def __init__(
        self,
        bus: Bus,
        channel: str = TRANSCRIPT_CHANNEL,
        *,
        title: str | None = "Last transcript",
    ) -> None:
        self._last = None
        super().__init__(bus, channel=channel, title=title)

    def build(self) -> None:
        with ui.column().classes("w-full").style("flex:1 1 auto;min-height:0;gap:0.45rem"):
            self.text = ui.label("waiting for speech...").classes("w-full").style(
                "flex:1 1 auto;min-height:0;overflow:auto;white-space:pre-wrap;"
                "word-break:break-word;color:var(--ctp-text);font-size:1.15rem;"
                "line-height:1.35;background:var(--ctp-crust);border-radius:0.5rem;"
                "padding:0.65rem;"
            )
            with ui.row().classes("w-full items-center").style("gap:0.35rem"):
                self.keywords = ui.row().classes("items-center").style("gap:0.3rem")
                self.meta = ui.label("").style(
                    "margin-left:auto;color:var(--ctp-subtext);font-size:0.78rem"
                )

    def on_data(self, value) -> None:
        if value is self._last:
            return
        self._last = value

        if not isinstance(value, Transcript):
            self.text.set_text(str(value))
            self._set_keywords([])
            self.meta.set_text("")
            return

        self.text.set_text(value.text or "No transcript text")
        self._set_keywords([k.keyword.name for k in value.keywords or []])
        language = value.language.value if value.language is not None else "unknown"
        self.meta.set_text(f"{language} / {value.language_probability:.0%}")

    def _set_keywords(self, keywords: list[str]) -> None:
        self.keywords.clear()
        with self.keywords:
            if not keywords:
                ui.label("no keywords").style("color:var(--ctp-subtext);font-size:0.78rem")
                return
            for keyword in keywords:
                ui.badge(keyword).props("outline").style(
                    "color:var(--ctp-green);border-color:var(--ctp-green)"
                )
