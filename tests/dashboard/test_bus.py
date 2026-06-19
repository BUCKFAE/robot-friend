"""Browser-free unit tests for the dashboard Bus (runs under default `uv run pytest`)."""
from robot_friend.dashboard.bus import Bus


def test_latest_returns_most_recent_and_default():
    bus = Bus()
    assert bus.latest("temp") is None
    assert bus.latest("temp", 0) == 0
    bus.publish("temp", 51.2)
    bus.publish("temp", 52.0)
    assert bus.latest("temp") == 52.0


def test_subscribers_receive_each_published_value():
    bus = Bus()
    seen: list[int] = []
    bus.subscribe("n", seen.append)
    bus.publish("n", 1)
    bus.publish("n", 2)
    assert seen == [1, 2]


def test_subscribers_are_per_channel():
    bus = Bus()
    seen: list[int] = []
    bus.subscribe("a", seen.append)
    bus.publish("b", 99)  # different channel: subscriber must not fire
    assert seen == []


def test_channels_lists_only_published_channels():
    bus = Bus()
    bus.publish("a", 1)
    bus.publish("b", 2)
    assert sorted(bus.channels()) == ["a", "b"]
