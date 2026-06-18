import argparse
import os

from nicegui import app, ui

from robot_friend.dashboard.app import bus, controls, logs, streams
from robot_friend.dashboard.diagnostics_scenario import DiagnosticsDemoScenario
from robot_friend.dashboard.sources.data_source import DashboardDataSource
from robot_friend.dashboard.sources.dataclass import FakeDataclassSource
from robot_friend.dashboard.sources.logs import FakeLogSource, LogSource
from robot_friend.dashboard.sources.speech import SpeechSource
from robot_friend.dashboard.sources.video import SCENARIOS, FakeVideoSource, VideoSource
from robot_friend.utils.finch_logger.finch_logger import finch_logger


def _build_sources(scenario: str | None) -> list[DashboardDataSource]:
    if scenario:
        return [
            FakeVideoSource(streams, scenario=scenario),
            FakeLogSource(logs, scenario=scenario),
            FakeDataclassSource(scenario=scenario),
        ]
    return [VideoSource(streams, controls), SpeechSource(controls), LogSource(logs)]


def main() -> None:
    parser = argparse.ArgumentParser(description="robot-friend diagnostics dashboard")
    parser.add_argument(
        "--demo-scenario",
        default=None,
        help="The demo scenario",
        choices=list(SCENARIOS) + [d.name for d in DiagnosticsDemoScenario],
    )
    parser.add_argument("--host", default=os.environ.get("DIAGNOSTICS_HOST", "0.0.0.0"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("DIAGNOSTICS_PORT", "8080"))
    )
    args = parser.parse_args()

    diagnostics_scenario = _scenario_name(args.demo_scenario) if args.demo_scenario else None
    finch_logger.info("Demo scenario: %s", diagnostics_scenario)
    sources = _build_sources(diagnostics_scenario)

    @app.on_startup
    def _start_sources() -> None:
        for source in sources:
            source.start(bus)

    mode = f"demo:{diagnostics_scenario}" if diagnostics_scenario else "live"
    finch_logger.info(
        "diagnostics dashboard (%s) on http://%s:%s/", mode, args.host, args.port
    )
    ui.run(
        host=args.host,
        port=args.port,
        title="Finch Diagnostics",
        favicon="🤖",
        dark=True,
        show=False,
        reload=False,
    )


def _scenario_name(scenario: str | None) -> str:
    if scenario is None:
        return "nominal"
    if scenario == "DEMO_SIMPLE":
        return "nominal"
    return scenario


if __name__ in {"__main__", "__mp_main__"}:
    main()
