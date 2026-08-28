"""Tests for viewer time cursor commands."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from gradio_rerun import Rerun
from gradio_rerun.commands import SetTimeUpdate, TimeControlCommand, set_time


class SetTimeTest(unittest.TestCase):
    """Test command construction and time conversion."""

    def command(self, update: SetTimeUpdate) -> TimeControlCommand:
        command = update["command"]
        self.assertEqual(update, {"command": command, "__type__": "update"})
        return command

    def test_sequence_uses_active_timeline_by_default(self) -> None:
        command = self.command(set_time(sequence=42))

        self.assertEqual(command["type"], "time_ctrl")
        self.assertEqual(command["timeline"], None)
        self.assertEqual(command["time"], 42)
        self.assertEqual(command["play"], False)
        self.assertIsInstance(command["id"], str)

    def test_temporal_values_are_converted_to_nanoseconds(self) -> None:
        duration = self.command(set_time("elapsed", duration=1.5, play=True))
        timestamp = self.command(
            set_time("capture_time", timestamp=datetime(1970, 1, 1, tzinfo=timezone.utc)),
        )

        self.assertEqual(duration["time"], 1_500_000_000)
        self.assertTrue(duration["play"])
        self.assertEqual(timestamp["time"], 0)

    def test_exactly_one_time_value_is_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly one"):
            set_time()  # type: ignore[call-overload]

        with self.assertRaisesRegex(ValueError, "exactly one"):
            set_time(sequence=1, duration=1.0)  # type: ignore[call-overload]

    def test_repeated_commands_have_distinct_ids(self) -> None:
        first = self.command(set_time(sequence=7))
        second = self.command(set_time(sequence=7))

        self.assertNotEqual(first["id"], second["id"])

    def test_component_value_remains_recording_data(self) -> None:
        component = Rerun(render=False)

        value = component.postprocess("https://example.com/recording.rrd")

        self.assertEqual(
            value.model_dump(),  # type: ignore[union-attr]
            ["https://example.com/recording.rrd"],
        )


if __name__ == "__main__":
    unittest.main()
