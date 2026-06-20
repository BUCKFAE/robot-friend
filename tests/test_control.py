"""RobotControls is the robot-side control state the dashboard commands via POST /control."""
from robot_friend.control import RobotControls


def test_apply_sets_camera_and_sound_and_notifies():
    controls = RobotControls()
    notified: list = []
    controls.on_sound_device_changed(notified.append)

    controls.apply({"camera_index": 2, "sound_device": 5})

    assert controls.camera_index == 2
    assert controls.sound_device == 5
    assert notified == [5]


def test_apply_leaves_absent_keys_unchanged():
    controls = RobotControls()
    controls.set_camera_index(1)
    controls.apply({"sound_device": 7})  # no camera_index -> camera unchanged
    assert controls.camera_index == 1
    assert controls.sound_device == 7


def test_devices_payload_has_options_and_selection():
    payload = RobotControls().devices_payload()
    assert set(payload) == {"camera", "sound", "selected"}
    assert payload["selected"] == {"camera_index": 0, "sound_device": None}
    assert len(payload["camera"]) >= 1  # always at least a fallback option
    assert len(payload["sound"]) >= 1
