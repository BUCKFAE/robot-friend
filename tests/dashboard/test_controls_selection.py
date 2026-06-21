"""Browser-free unit tests for the controls selection snapshot synced across clients."""
from robot_friend.dashboard.controls import ControlSelection, DashboardControls


def test_selection_defaults():
    controls = DashboardControls()
    assert controls.selection() == ControlSelection(camera_index=0, sound_device=None)


def test_selection_reflects_setters():
    controls = DashboardControls()
    controls.set_camera_index(2)
    controls.set_sound_device("USB mic")
    assert controls.selection() == ControlSelection(camera_index=2, sound_device="USB mic")
