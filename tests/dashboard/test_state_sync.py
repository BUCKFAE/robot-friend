"""Browser-free unit tests for StateSync — the dashboard's cross-client state primitive.

Covers the contract the panels depend on: seed-once, dedupe, echo-skip, and the
applying-guard that stops a programmatic widget update from bouncing back onto the bus.
"""
from robot_friend.dashboard.bus import Bus
from robot_friend.dashboard.panels.state_sync import StateSync


def test_seed_publishes_only_when_channel_empty():
    bus = Bus()
    StateSync(bus, "c").seed("v1")
    assert bus.latest("c") == "v1"

    # A second client seeding later must NOT clobber what peers changed it to.
    bus.publish("c", "v2")
    later = StateSync(bus, "c")
    later.seed("v3")
    assert bus.latest("c") == "v2"   # bus stays authoritative
    assert later.state == "v3"        # local view is the seed until the next poll


def test_publish_broadcasts_changes_and_dedupes():
    bus = Bus()
    sync = StateSync(bus, "c")
    sync.seed("a")

    received: list[str] = []
    bus.subscribe("c", received.append)

    sync.publish("a")  # unchanged -> no broadcast
    sync.publish("b")  # changed   -> broadcast
    assert received == ["b"]
    assert sync.state == "b"


def test_receive_applies_and_skips_own_echo():
    bus = Bus()
    sync = StateSync(bus, "c")
    sync.seed("a")

    applied: list[str] = []
    sync.receive("a", applied.append)  # echo of current state -> skip
    sync.receive("b", applied.append)  # genuine peer update   -> apply
    assert applied == ["b"]
    assert sync.state == "b"


def test_publish_is_suppressed_while_applying():
    """A widget write during apply (which can re-fire change handlers) must not loop."""
    bus = Bus()
    sync = StateSync(bus, "c")
    sync.seed("a")

    broadcasts: list[str] = []
    bus.subscribe("c", broadcasts.append)

    def apply(_value):
        assert sync.applying is True
        sync.publish("loop")  # must be a no-op while applying

    sync.receive("b", apply)
    assert broadcasts == []      # nothing re-broadcast from inside apply
    assert sync.applying is False
    assert sync.state == "b"
