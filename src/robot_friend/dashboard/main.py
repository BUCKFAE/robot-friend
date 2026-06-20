import argparse
import os

from nicegui import app, ui

from robot_friend.dashboard import app as dashboard_app
from robot_friend.dashboard.app import bus, logs, streams
from robot_friend.dashboard.controls_client import RobotControlsClient
from robot_friend.dashboard.servos_client import RobotServosClient
from robot_friend.dashboard.dashboard_scenario import DashboardDemoScenario
from robot_friend.dashboard.sources.data_source import DashboardDataSource
from robot_friend.dashboard.sources.dataclass import FakeDataclassSource
from robot_friend.dashboard.sources.logs import FakeLogSource, LogSource
from robot_friend.dashboard.sources.robot_log_source import RobotLogSource
from robot_friend.dashboard.sources.telemetry_source import TelemetrySource
from robot_friend.dashboard.sources.video import SCENARIOS, FakeVideoSource, VideoSource
from robot_friend.utils.finch_logger.finch_logger import finch_logger


def _build_sources(scenario: str | None, robot_url: str) -> list[DashboardDataSource]:
    if scenario:
        return [
            FakeVideoSource(streams, scenario=scenario),
            FakeLogSource(logs, scenario=scenario),
            FakeDataclassSource(scenario=scenario),
        ]
    # Live mode: attach to the running robot. Video is proxied from its MJPEG streams;
    # detections/perf/transcript come over telemetry; the Logs panel merges the robot's
    # own logs (RobotLogSource) with the dashboard's connection logs (LogSource).
    return [
        VideoSource(streams, robot_url),
        TelemetrySource(robot_url),
        RobotLogSource(logs, robot_url),
        LogSource(logs),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="robot-friend dashboard")
    parser.add_argument(
        "--demo-scenario",
        default=None,
        help="The demo scenario",
        choices=list(SCENARIOS) + [d.name for d in DashboardDemoScenario],
    )
    parser.add_argument("--host", default=os.environ.get("DASHBOARD_HOST", "0.0.0.0"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("DASHBOARD_PORT", "8080"))
    )
    parser.add_argument(
        "--robot-url",
        default=os.environ.get("ROBOT_URL", "http://localhost:8081"),
        help="Base URL of the running robot (robot_friend.main) to attach to in live mode",
    )
    args = parser.parse_args()

    dashboard_scenario = _scenario_name(args.demo_scenario) if args.demo_scenario else None
    finch_logger.info("Demo scenario: %s", dashboard_scenario)
    if dashboard_scenario is None:
        # Live: drive the ControlPanel against the robot (enumerate + command its devices).
        dashboard_app.controls = RobotControlsClient(args.robot_url)
        # Live: drive the ServoPanel against the robot (read + command its servos).
        dashboard_app.servos = RobotServosClient(args.robot_url)
    sources = _build_sources(dashboard_scenario, args.robot_url)

    @app.on_startup
    def _start_sources() -> None:
        for source in sources:
            source.start(bus)

    mode = f"demo:{dashboard_scenario}" if dashboard_scenario else "live"
    finch_logger.info(
        "dashboard (%s) on http://%s:%s/", mode, args.host, args.port
    )
    ui.run(
        host=args.host,
        port=args.port,
        title="Finch Dashboard",
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
