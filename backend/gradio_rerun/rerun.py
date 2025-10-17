"""gr.SimpleImage() component."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from gradio import processing_utils
from gradio.components.base import Component, StreamingOutput
from gradio.data_classes import FileData, GradioRootModel, MediaStreamChunk
from gradio.events import EventListener

if TYPE_CHECKING:
    from gradio.components.base import Component


class RerunData(GradioRootModel):
    """
    Data model for Rerun component is a list of data sources.

    `FileData` is used for data served from Gradio, while `str` is used for URLs Rerun will open from a remote server.
    """

    root: Sequence[FileData | Path | str] | None


class Rerun(Component, StreamingOutput):
    """Creates a Rerun viewer component that can be used to display the output of a Rerun stream."""

    EVENTS: list[EventListener | str] = [
        EventListener(
            "play",
            doc="Fired when timeline playback starts. Callback should accept a parameter of type "
            "`gradio_rerun.events.Play`",
        ),
        EventListener(
            "pause",
            doc="Fired when timeline pauseback starts. Callback should accept a parameter of type "
            "`gradio_rerun.events.Pause`",
        ),
        EventListener(
            "time_update",
            doc="Fired when time updates. Callback should accept a parameter of type `gradio_rerun.events.TimeUpdate`.",
        ),
        EventListener(
            "timeline_change",
            doc="Fired when a timeline is selected. Callback should accept a parameter of type "
            "`gradio_rerun.events.TimelineChange`.",
        ),
        EventListener(
            "selection_change",
            doc="Fired when the selection changes. Callback should accept a parameter of type "
            "`gradio_rerun.events.SelectionChange`.",
        ),
    ]

    data_model = RerunData

    def __init__(
        self,
        value: list[Path | str] | Path | str | bytes | Callable | None = None,
        *,
        label: str | None = None,
        every: float | None = None,
        show_label: bool | None = None,
        container: bool = True,
        scale: int | None = None,
        min_width: int = 160,
        height: int | str = 640,
        visible: bool = True,
        streaming: bool = False,
        elem_id: str | None = None,
        elem_classes: list[str] | str | None = None,
        render: bool = True,
        panel_states: dict[str, Any] | None = None,
    ):
        """
        Initialize a Rerun Viewer block.

        Args:
            value: Takes a singular or list of RRD resources. Each RRD can be a Path, a string containing a url,
                or a binary blob containing encoded RRD data. If callable, the function will be called whenever the app
                loads to set the initial value of the component.
            label: The label for this component. Appears above the component and is also used as the header if there
                are a table of examples for this component. If None and used in a `gr.Interface`, the label will be
                the name of the parameter this component is assigned to.
            every: If `value` is a callable, run the function 'every' number of seconds while the client connection is
                open. Has no effect otherwise. Queue must be enabled. The event can be accessed (e.g. to cancel it) via
                this component's .load_event attribute.
            show_label: if True, will display label.
            container: If True, will place the component in a container providing some extra padding around the border.
            scale: relative size compared to adjacent Components.
                For example if Components A and B are in a Row, and A has scale=2, and B has scale=1, A will be twice
                as wide as B. Should be an integer. scale applies in Rows, and to top-level Components in Blocks where
                fill_height=True.
            min_width: minimum pixel width, will wrap if not sufficient screen space to satisfy this value.
                If a certain scale value results in this Component being narrower than `min_width`, the `min_width`
                parameter will be respected first.
            height: height of component in pixels. If a string is provided, will be interpreted as a CSS value.
                If None, will be set to 640px.
            visible: If False, component will be hidden.
            streaming: If True, the data should be incrementally yielded from the source as `bytes` returned by
                calling `.read()` on an `rr.binary_stream()`
            elem_id: An optional string that is assigned as the id of this component in the HTML DOM.
                Can be used for targeting CSS styles.
            elem_classes: An optional list of strings that are assigned as the classes of this component in
                the HTML DOM, can be used for targeting CSS styles.
            render: If False, component will not render be rendered in the Blocks context.
                Should be used if the intention is to assign event listeners now but render the component later.
            panel_states: Force viewer panels to a specific state.
                Any panels set cannot be toggled by the user in the viewer.
                Panel names are "top", "blueprint", "selection", and "time".
                States are "hidden", "collapsed", and "expanded".

        """
        self.height = height
        self.streaming = streaming
        self.panel_states = panel_states
        super().__init__(
            label=label,
            every=every,
            show_label=show_label,
            container=container,
            scale=scale,
            min_width=min_width,
            interactive=False,  # Rerun is an output-component only
            visible=visible,
            elem_id=elem_id,
            elem_classes=elem_classes,
            render=render,
            value=value,
        )

    def get_config(self):
        config = super().get_config()
        config["panel_states"] = self.panel_states
        return config

    def preprocess(self, payload: RerunData | None) -> RerunData | None:
        """
        Do not accept input in this component.

        Args:
            payload: A `RerunData` object.

        Returns:
            A `RerunData` object.

        """
        if payload is None:
            return None
        return payload

    def postprocess(self, value: list[Path | str] | Path | str | bytes) -> RerunData | bytes:
        """
        Post process the value.

        Args:
            value: The value to send over to the Rerun viewer on the front-end.

        Returns:
            A FileData object containing the image data.

        """
        if value is None:
            return RerunData(root=None)

        if isinstance(value, bytes):
            if self.streaming:
                return value
            file_path = processing_utils.save_bytes_to_cache(value, "rrd", cache_dir=self.GRADIO_CACHE)
            return RerunData(root=[FileData(path=file_path)])

        if not isinstance(value, list):
            value = [value]

        def is_url(url_like: Path | str) -> bool:
            if isinstance(url_like, Path):
                return False
            return url_like.startswith(("http://", "https://"))

        return RerunData(
            root=[
                FileData(
                    path=str(file),
                    orig_name=Path(file).name,
                    size=Path(file).stat().st_size,
                )
                if not is_url(file)
                else file
                for file in value
            ]
        )

    async def stream_output(
        self,
        value: bytes | None,
        output_id: str,
        first_chunk: bool,  # noqa: ARG002
    ) -> tuple[MediaStreamChunk | None, dict]:
        output_file = {
            "path": output_id,
            "is_stream": True,
            "orig_name": "recording.rrd",
            "meta": {"_type": "gradio.FileData"},
        }
        if value is None:
            return None, output_file

        return MediaStreamChunk(data=value, duration=0.1, extension=".ts"), output_file

    async def combine_stream(
        self,
        stream: list[bytes],
        desired_output_format: str | None = None,
        only_file=False,
    ) -> RerunData | FileData:
        return RerunData(
            root=[
                FileData(path=processing_utils.save_bytes_to_cache(value, "rrd", cache_dir=self.GRADIO_CACHE))
                for value in stream
            ]
        )

    def check_streamable(self):
        return self.streaming

    def example_payload(self) -> Any:
        return []

    def example_value(self) -> Any:
        return [
            "https://app.rerun.io/version/0.16.0/examples/detect_and_track_objects.rrd",
            "https://app.rerun.io/version/0.16.0/examples/dna.rrd",
        ]
