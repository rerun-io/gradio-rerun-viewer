"""Commands sent from Gradio callbacks to the embedded Rerun viewer."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias, overload

from rerun.time import to_nanos, to_nanos_since_epoch

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    import numpy as np


SetTimeCommand: TypeAlias = dict[str, str | int | bool | None]

__all__ = ["SetTimeCommand", "set_time"]


@overload
def set_time(timeline: str | None = None, *, sequence: int, play: bool = False) -> SetTimeCommand: ...


@overload
def set_time(
    timeline: str | None = None,
    *,
    duration: int | float | timedelta | np.timedelta64,
    play: bool = False,
) -> SetTimeCommand: ...


@overload
def set_time(
    timeline: str | None = None,
    *,
    timestamp: int | float | datetime | np.datetime64,
    play: bool = False,
) -> SetTimeCommand: ...


def set_time(
    timeline: str | None = None,
    *,
    sequence: int | None = None,
    duration: int | float | timedelta | np.timedelta64 | None = None,
    timestamp: int | float | datetime | np.datetime64 | None = None,
    play: bool = False,
) -> SetTimeCommand:
    """
    Create a command that sets the embedded viewer's time cursor.

    Return this command from a Gradio callback whose output is a [`Rerun`][gradio_rerun.Rerun] component.
    If `timeline` is omitted, the viewer uses its active timeline.
    Exactly one of `sequence`, `duration`, or `timestamp` must be set.

    Example:
        ```python
        from gradio_rerun.commands import set_time

        def seek(frame: int):
            return set_time(sequence=frame)
        ```

    """
    if sum(value is not None for value in (sequence, duration, timestamp)) != 1:
        raise ValueError("set_time expects exactly one of sequence, duration, or timestamp")

    if sequence is not None:
        time = sequence
    elif duration is not None:
        time = to_nanos(duration)
    else:
        assert timestamp is not None
        time = to_nanos_since_epoch(timestamp)

    return {
        "command": "set_time",
        "timeline": timeline,
        "time": time,
        "play": play,
    }
