---
tags: [gradio-custom-component, SimpleImage, multimodal data, visualization, machine learning, robotics]
title: gradio_rerun
short_description: Rerun viewer with Gradio
colorFrom: blue
colorTo: yellow
sdk: gradio
pinned: false
app_file: space.py
---

# `gradio_rerun`
<a href="https://pypi.org/project/gradio_rerun/" target="_blank"><img alt="PyPI - Version" src="https://img.shields.io/pypi/v/gradio_rerun"></a> <a href="https://github.com/rerun-io/gradio-rerun-viewer/issues" target="_blank"><img alt="Static Badge" src="https://img.shields.io/badge/Issues-white?logo=github&logoColor=black"></a> <a href="https://huggingface.co/spaces/rerun/gradio-rerun-viewer/discussions" target="_blank"><img alt="Static Badge" src="https://img.shields.io/badge/%F0%9F%A4%97%20Discuss-%23097EFF?style=flat&logoColor=black"></a>

Rerun viewer with Gradio

## Installation

```bash
pip install gradio_rerun
```

## Usage

```python
"""
Demonstrates integrating Rerun visualization with Gradio.

Provides example implementations of data streaming, keypoint annotation, and dynamic
visualization across multiple Gradio tabs using Rerun's recording and visualization capabilities.
"""

import math
import os
import tempfile
import time
import uuid

import cv2
import gradio as gr
import rerun as rr
import rerun.blueprint as rrb
from gradio_rerun import Rerun
from gradio_rerun.events import (
    SelectionChange,
    TimelineChange,
    TimeUpdate,
)

try:
    from .color_grid import build_color_grid
except ImportError:
    # For running the demo directly using `gradio cc dev`.
    from color_grid import build_color_grid  # type: ignore[no-redef,import-not-found]


# Whenever we need a recording, we construct a new recording stream.
# As long as the app and recording IDs remain the same, the data
# will be merged by the Viewer.
def get_recording(recording_id: str) -> rr.RecordingStream:
    return rr.RecordingStream(application_id="rerun_example_gradio", recording_id=recording_id)


# A task can directly log to a binary stream, which is routed to the embedded viewer.
# Incremental chunks are yielded to the viewer using `yield stream.read()`.
#
# This is the preferred way to work with Rerun in Gradio since your data can be immediately and
# incrementally seen by the viewer. Also, there are no ephemeral RRDs to cleanup or manage.
def streaming_repeated_blur(recording_id: str, img):
    # Here we get a recording using the provided recording id.
    rec = get_recording(recording_id)
    stream = rec.binary_stream()  # type: ignore

    if img is None:
        raise gr.Error("Must provide an image to blur.")

    blueprint = rrb.Blueprint(
        rrb.Horizontal(
            rrb.Spatial2DView(origin="image/original"),
            rrb.Spatial2DView(origin="image/blurred"),
        ),
        collapse_panels=True,
    )

    rec.send_blueprint(blueprint)
    rec.set_time("iteration", sequence=0)
    rec.log("image/original", rr.Image(img))
    yield stream.read()

    blur = img
    for i in range(100):
        rec.set_time("iteration", sequence=i)

        # Pretend blurring takes a while so we can see streaming in action.
        time.sleep(0.1)
        blur = cv2.GaussianBlur(blur, (5, 5), 0)
        rec.log("image/blurred", rr.Image(blur))

        # Each time we yield bytes from the stream back to Gradio, they
        # are incrementally sent to the viewer. Make sure to yield any time
        # you want the user to be able to see progress.
        yield stream.read()


# In this example the user is able to add keypoints to an image visualized in Rerun.
# These keypoints are stored in the global state, we use the session id to keep track of which keypoints belong
# to a specific session (https://www.gradio.app/guides/state-in-blocks).
#
# The current session can be obtained by adding a parameter of type `gradio.Request` to your event listener functions.
Keypoint = tuple[float, float]
keypoints_per_session_per_sequence_index: dict[str, dict[int, list[Keypoint]]] = {}


def get_keypoints_for_user_at_sequence_index(request: gr.Request, sequence: int) -> list[Keypoint]:
    if request.session_hash is None:
        raise ValueError("Session hash is None")
    per_sequence = keypoints_per_session_per_sequence_index[request.session_hash]
    if sequence not in per_sequence:
        per_sequence[sequence] = []

    return per_sequence[sequence]


def initialize_instance(request: gr.Request) -> None:
    if request.session_hash is None:
        raise ValueError("Session hash is None")
    keypoints_per_session_per_sequence_index[request.session_hash] = {}


def cleanup_instance(request: gr.Request) -> None:
    if request.session_hash is not None and request.session_hash in keypoints_per_session_per_sequence_index:
        del keypoints_per_session_per_sequence_index[request.session_hash]


# In this function, the `request` and `evt` parameters will be automatically injected by Gradio when this
# event listener is fired.
#
# `SelectionChange` is a subclass of `EventData`: https://www.gradio.app/docs/gradio/eventdata
# `gr.Request`: https://www.gradio.app/main/docs/gradio/request
def register_keypoint(
    active_recording_id: str,
    current_timeline: str,
    current_time: float,
    request: gr.Request,
    change: SelectionChange,
):
    if active_recording_id == "":
        return

    if current_timeline != "iteration":
        return

    evt = change.payload

    # We can only log a keypoint if the user selected only a single item.
    if len(evt.items) != 1:
        return
    item = evt.items[0]

    # If the selected item isn't an entity, or we don't have its position, then bail out.
    if item.type != "entity" or item.position is None:
        return

    # Now we can produce a valid keypoint.
    rec = get_recording(active_recording_id)
    stream = rec.binary_stream()  # type: ignore

    # We round `current_time` toward 0, because that gives us the sequence index
    # that the user is currently looking at, due to the Viewer's latest-at semantics.
    index = math.floor(current_time)

    # We keep track of the keypoints per sequence index for each user manually.
    keypoints = get_keypoints_for_user_at_sequence_index(request, index)
    keypoints.append((item.position[0], item.position[1]))

    rec.set_time("iteration", sequence=index)
    rec.log(f"{item.entity_path}/keypoint", rr.Points2D(keypoints, radii=2))

    yield stream.read()


def track_current_time(evt: TimeUpdate):
    return evt.payload.time


def track_current_timeline_and_time(evt: TimelineChange):
    return evt.payload.timeline, evt.payload.time


# However, if you have a workflow that creates an RRD file instead, you can still send it
# directly to the viewer by simply returning the path to the RRD file.
#
# This may be helpful if you need to execute a helper tool written in C++ or Rust that can't
# be easily modified to stream data directly via Gradio.
#
# In this case you may want to clean up the RRD file after it's sent to the viewer so that you
# don't accumulate too many temporary files.
@rr.thread_local_stream("rerun_example_cube_rrd")
def create_cube_rrd(x, y, z, pending_cleanup):
    cube = build_color_grid(int(x), int(y), int(z), twist=0)
    rr.log("cube", rr.Points3D(cube.positions, colors=cube.colors, radii=0.5))

    # Simulate delay
    time.sleep(x / 10)

    # We eventually want to clean up the RRD file after it's sent to the viewer, so tracking
    # any pending files to be cleaned up when the state is deleted.
    temp = tempfile.NamedTemporaryFile(prefix="cube_", suffix=".rrd", delete=False)
    pending_cleanup.append(temp.name)

    blueprint = rrb.Spatial3DView(origin="cube")
    rr.save(temp.name, default_blueprint=blueprint)

    # Just return the name of the file -- Gradio will convert it to a FileData object
    # and send it to the viewer.
    return temp.name


def cleanup_cube_rrds(pending_cleanup: list[str]) -> None:
    for f in pending_cleanup:
        os.unlink(f)


with gr.Blocks() as demo:
    with gr.Tab("Streaming"):
        with gr.Row():
            img = gr.Image(interactive=True, label="Image")
            with gr.Column():
                stream_blur = gr.Button("Stream Repeated Blur")

        with gr.Row():
            viewer = Rerun(
                streaming=True,
                panel_states={
                    "time": "collapsed",
                    "blueprint": "hidden",
                    "selection": "hidden",
                },
            )

        # We make a new recording id, and store it in a Gradio's session state.
        recording_id = gr.State(uuid.uuid4())

        # Also store the current timeline and time of the viewer in the session state.
        current_timeline = gr.State("")
        current_time = gr.State(0.0)

        # When registering the event listeners, we pass the `recording_id` in as input in order to create
        # a recording stream using that id.
        stream_blur.click(
            # Using the `viewer` as an output allows us to stream data to it by yielding bytes from the callback.
            streaming_repeated_blur,
            inputs=[recording_id, img],
            outputs=[viewer],
        )
        viewer.selection_change(
            register_keypoint,
            inputs=[recording_id, current_timeline, current_time],
            outputs=[viewer],
        )
        viewer.time_update(track_current_time, outputs=[current_time])
        viewer.timeline_change(track_current_timeline_and_time, outputs=[current_timeline, current_time])
    with gr.Tab("Dynamic RRD"):
        pending_cleanup = gr.State([], time_to_live=10, delete_callback=cleanup_cube_rrds)
        with gr.Row():
            x_count = gr.Number(minimum=1, maximum=10, value=5, precision=0, label="X Count")
            y_count = gr.Number(minimum=1, maximum=10, value=5, precision=0, label="Y Count")
            z_count = gr.Number(minimum=1, maximum=10, value=5, precision=0, label="Z Count")
        with gr.Row():
            create_rrd = gr.Button("Create RRD")
        with gr.Row():
            viewer = Rerun(
                streaming=True,
                panel_states={
                    "time": "collapsed",
                    "blueprint": "hidden",
                    "selection": "hidden",
                },
            )
        create_rrd.click(
            create_cube_rrd,
            inputs=[x_count, y_count, z_count, pending_cleanup],
            outputs=[viewer],
        )

    with gr.Tab("Hosted RRD"):
        with gr.Row():
            # It may be helpful to point the viewer to a hosted RRD file on another server.
            # If an RRD file is hosted via http, you can just return a URL to the file.
            choose_rrd = gr.Dropdown(
                label="RRD",
                choices=[
                    f"{rr.bindings.get_app_url()}/examples/arkit_scenes.rrd",  # type: ignore[private-use]
                    f"{rr.bindings.get_app_url()}/examples/dna.rrd",  # type: ignore[private-use]
                    f"{rr.bindings.get_app_url()}/examples/plots.rrd",  # type: ignore[private-use]
                ],
            )
        with gr.Row():
            viewer = Rerun(
                streaming=True,
                panel_states={
                    "time": "collapsed",
                    "blueprint": "hidden",
                    "selection": "hidden",
                },
            )
        choose_rrd.change(lambda x: x, inputs=[choose_rrd], outputs=[viewer])

    demo.load(initialize_instance)
    demo.close(cleanup_instance)


if __name__ == "__main__":
    demo.launch(ssr_mode=False)

```

## `Rerun`

### Initialization

<table>
<thead>
<tr>
<th align="left">name</th>
<th align="left" style="width: 25%;">type</th>
<th align="left">default</th>
<th align="left">description</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left"><code>value</code></td>
<td align="left" style="width: 25%;">

```python
list[pathlib.Path | str]
    | pathlib.Path
    | str
    | bytes
    | collections.abc.Callable
    | None
```

</td>
<td align="left"><code>None</code></td>
<td align="left">Takes a singular or list of RRD resources. Each RRD can be a Path, a string containing a url,</td>
</tr>

<tr>
<td align="left"><code>label</code></td>
<td align="left" style="width: 25%;">

```python
str | None
```

</td>
<td align="left"><code>None</code></td>
<td align="left">The label for this component. Appears above the component and is also used as the header if there</td>
</tr>

<tr>
<td align="left"><code>every</code></td>
<td align="left" style="width: 25%;">

```python
float | None
```

</td>
<td align="left"><code>None</code></td>
<td align="left">If `value` is a callable, run the function 'every' number of seconds while the client connection is</td>
</tr>

<tr>
<td align="left"><code>show_label</code></td>
<td align="left" style="width: 25%;">

```python
bool | None
```

</td>
<td align="left"><code>None</code></td>
<td align="left">if True, will display label.</td>
</tr>

<tr>
<td align="left"><code>container</code></td>
<td align="left" style="width: 25%;">

```python
bool
```

</td>
<td align="left"><code>True</code></td>
<td align="left">If True, will place the component in a container providing some extra padding around the border.</td>
</tr>

<tr>
<td align="left"><code>scale</code></td>
<td align="left" style="width: 25%;">

```python
int | None
```

</td>
<td align="left"><code>None</code></td>
<td align="left">relative size compared to adjacent Components.</td>
</tr>

<tr>
<td align="left"><code>min_width</code></td>
<td align="left" style="width: 25%;">

```python
int
```

</td>
<td align="left"><code>160</code></td>
<td align="left">minimum pixel width, will wrap if not sufficient screen space to satisfy this value.</td>
</tr>

<tr>
<td align="left"><code>height</code></td>
<td align="left" style="width: 25%;">

```python
int | str
```

</td>
<td align="left"><code>640</code></td>
<td align="left">height of component in pixels. If a string is provided, will be interpreted as a CSS value.</td>
</tr>

<tr>
<td align="left"><code>visible</code></td>
<td align="left" style="width: 25%;">

```python
bool
```

</td>
<td align="left"><code>True</code></td>
<td align="left">If False, component will be hidden.</td>
</tr>

<tr>
<td align="left"><code>streaming</code></td>
<td align="left" style="width: 25%;">

```python
bool
```

</td>
<td align="left"><code>False</code></td>
<td align="left">If True, the data should be incrementally yielded from the source as `bytes` returned by</td>
</tr>

<tr>
<td align="left"><code>elem_id</code></td>
<td align="left" style="width: 25%;">

```python
str | None
```

</td>
<td align="left"><code>None</code></td>
<td align="left">An optional string that is assigned as the id of this component in the HTML DOM.</td>
</tr>

<tr>
<td align="left"><code>elem_classes</code></td>
<td align="left" style="width: 25%;">

```python
list[str] | str | None
```

</td>
<td align="left"><code>None</code></td>
<td align="left">An optional list of strings that are assigned as the classes of this component in</td>
</tr>

<tr>
<td align="left"><code>render</code></td>
<td align="left" style="width: 25%;">

```python
bool
```

</td>
<td align="left"><code>True</code></td>
<td align="left">If False, component will not render be rendered in the Blocks context.</td>
</tr>

<tr>
<td align="left"><code>panel_states</code></td>
<td align="left" style="width: 25%;">

```python
dict[str, typing.Any] | None
```

</td>
<td align="left"><code>None</code></td>
<td align="left">Force viewer panels to a specific state.</td>
</tr>
</tbody></table>


### Events

| name | description |
|:-----|:------------|
| `play` | Fired when timeline playback starts. Callback should accept a parameter of type `gradio_rerun.events.Play` |
| `pause` | Fired when timeline pauseback starts. Callback should accept a parameter of type `gradio_rerun.events.Pause` |
| `time_update` | Fired when time updates. Callback should accept a parameter of type `gradio_rerun.events.TimeUpdate`. |
| `timeline_change` | Fired when a timeline is selected. Callback should accept a parameter of type `gradio_rerun.events.TimelineChange`. |
| `selection_change` | Fired when the selection changes. Callback should accept a parameter of type `gradio_rerun.events.SelectionChange`. |



### User function

The impact on the users predict function varies depending on whether the component is used as an input or output for an event (or both).

- When used as an Input, the component only impacts the input signature of the user function.
- When used as an output, the component only impacts the return signature of the user function.

The code snippet below is accurate in cases where the component is used as both an input and an output.

- **As output:** Is passed, a `RerunData` object.
- **As input:** Should return, the value to send over to the Rerun viewer on the front-end.

 ```python
 def predict(
     value: RerunData | None
 ) -> list[pathlib.Path | str] | pathlib.Path | str | bytes:
     return value
 ```
 

## `RerunData`
```python
class RerunData(GradioRootModel):
    root: Sequence[FileData | Path | str] | None
```
