"""Commands sent from Gradio callbacks to the embedded Rerun viewer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict, cast, overload
from uuid import uuid4

from gradio import update as gradio_update
from rerun.time import to_nanos, to_nanos_since_epoch

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    import numpy as np


class _TimeControlCommand(TypedDict):
    """Serializable command consumed by the embedded viewer."""

    id: str
    type: Literal["time_ctrl"]
    timeline: str | None
    time: int
    play: bool


class _SetTimeUpdate(TypedDict):
    """Gradio property update containing a time-control command."""

    _command: _TimeControlCommand
    __type__: Literal["update"]


__all__ = ["set_time"]


@overload
def set_time(timeline: str | None = None, *, sequence: int, play: bool = False) -> _SetTimeUpdate: ...


@overload
def set_time(
    timeline: str | None = None,
    *,
    duration: int | float | timedelta | np.timedelta64,
    play: bool = False,
) -> _SetTimeUpdate: ...


@overload
def set_time(
    timeline: str | None = None,
    *,
    timestamp: int | float | datetime | np.datetime64,
    play: bool = False,
) -> _SetTimeUpdate: ...


def set_time(
    timeline: str | None = None,
    *,
    sequence: int | None = None,
    duration: int | float | timedelta | np.timedelta64 | None = None,
    timestamp: int | float | datetime | np.datetime64 | None = None,
    play: bool = False,
) -> _SetTimeUpdate:
    """
    Create a Gradio update that sets the embedded viewer's time cursor.

    Return this update from a Gradio callback whose output is a [`Rerun`][gradio_rerun.Rerun] component.
    The recording remains the component's value; the cursor update travels through a separate command property.
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
        time: int = sequence
    elif duration is not None:
        time = to_nanos(duration)
    else:
        assert timestamp is not None
        time = to_nanos_since_epoch(timestamp)

    command: _TimeControlCommand = _TimeControlCommand(
        id=uuid4().hex,
        type="time_ctrl",
        timeline=timeline,
        time=time,
        play=play,
    )
    return cast("_SetTimeUpdate", gradio_update(_command=command))
