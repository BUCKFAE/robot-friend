"""Live diagnostics web dashboard for the Finch robot.

A set of reusable NiceGUI panels arranged in a grid. Each panel reads a named
channel; a matching :class:`~robot_friend.diagnostics.sources.data_source.DataSource`
publishes onto it. Run it with the ``robot-friend-diagnostics`` entrypoint
(``--demo-scenario nominal`` for deterministic fake data with no hardware). See
``FinchObsidian/implementation-plans/diagnostics-dashboard.md``.
"""
