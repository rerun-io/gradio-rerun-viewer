"""Tests for viewer time cursor commands."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from gradio_rerun import Rerun
from gradio_rerun.commands import set_time


class SetTimeTest(unittest.TestCase):
    """Test command construction and time conversion."""

    def test_sequence_uses_active_timeline_by_default(self) -> None:
        command = set_time(sequence=42)

        self.assertEqual(
            command,
            {
                "command": "set_time",
                "timeline": None,
                "time": 42,
                "play": False,
            },
        )

    def test_temporal_values_are_converted_to_nanoseconds(self) -> None:
        duration = set_time("elapsed", duration=1.5, play=True)
        timestamp = set_time("capture_time", timestamp=datetime(1970, 1, 1, tzinfo=timezone.utc))

        self.assertEqual(duration["time"], 1_500_000_000)
        self.assertTrue(duration["play"])
        self.assertEqual(timestamp["time"], 0)

    def test_exactly_one_time_value_is_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly one"):
            set_time()

        with self.assertRaisesRegex(ValueError, "exactly one"):
            set_time(sequence=1, duration=1.0)  # type: ignore[call-overload]

    def test_component_serializes_command_as_its_value(self) -> None:
        component = Rerun(render=False)

        value = component.postprocess(set_time("frame", sequence=7))

        self.assertEqual(
            value.model_dump(),  # type: ignore[union-attr]
            {
                "command": "set_time",
                "timeline": "frame",
                "time": 7,
                "play": False,
            },
        )

    def test_component_rejects_unknown_commands(self) -> None:
        component = Rerun(render=False)

        with self.assertRaisesRegex(ValueError, "Unknown Rerun viewer command"):
            component.postprocess({"command": "unknown"})


if __name__ == "__main__":
    unittest.main()
