"""Events fired by the Rerun block."""

from __future__ import annotations

from typing import Any

from gradio import EventData
from rerun.event import (
    PlayEvent,
    PauseEvent,
    TimeUpdateEvent,
    TimelineChangeEvent,
    SelectionChangeEvent,
    _viewer_event_from_json_str,
)


class Play(EventData):
    def __init__(self, target: Any, data: Any):
        super().__init__(target, data)

        event = _viewer_event_from_json_str(data)
        assert event.type == "play"
        self.payload: PlayEvent = event


class Pause(EventData):
    def __init__(self, target: Any, data: Any):
        super().__init__(target, data)

        event = _viewer_event_from_json_str(data)
        assert event.type == "pause"
        self.payload: PauseEvent = event


class TimeUpdate(EventData):
    """Event triggered when the time is updated in the viewer."""

    def __init__(self, target: Any, data: Any) -> None:
        """
        Initialize a TimeUpdate event.

        Args:
            target (Any): The object that triggered the time update event.
            data (Any): The new time value.

        """
        super().__init__(target, data)

        event = _viewer_event_from_json_str(data)
        assert event.type == "time_update"
        self.payload: TimeUpdateEvent = event



class TimelineChange(EventData):
    """Event triggered when the timeline changes in the viewer."""

    def __init__(self, target: Any, data: Any) -> None:
        """
        Initialize a TimelineChange event.

        Args:
            target (Any): The object that triggered the timeline change event.
            data (Any): A dictionary containing timeline and time information.

        """
        super().__init__(target, data)

        event = _viewer_event_from_json_str(data)
        assert event.type == "timeline_change"
        self.payload: TimelineChangeEvent = event


class SelectionChange(EventData):
    def __init__(self, target: Any, data: Any):
        super().__init__(target, data)

        event = _viewer_event_from_json_str(data)
        assert event.type == "selection_change"
        self.payload: SelectionChangeEvent = event


