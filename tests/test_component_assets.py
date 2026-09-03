"""Regression tests for the generated Gradio component bundle."""

from __future__ import annotations

import unittest
from typing import Any

import gradio as gr
from fastapi.testclient import TestClient
from gradio.routes import App
from gradio_rerun import Rerun
from httpx import Response


class ComponentAssetTest(unittest.TestCase):
    """Verify assets required by Gradio's custom-component loader."""

    def test_gradio_serves_component_runtime(self) -> None:
        with gr.Blocks() as demo:
            Rerun()

        with TestClient(App.create_app(demo)) as client:
            config: dict[str, Any] = client.get("/config").json()
            component: dict[str, Any] = next(item for item in config["components"] if item["type"] == "rerun")
            component_id: str = component["component_class_id"]
            runtime_url: str = f"/gradio_api/custom_component/{component_id}/client/component/svelte_runtime_entry.js"

            response: Response = client.get(runtime_url)

        self.assertEqual(response.status_code, 200, response.text)


if __name__ == "__main__":
    unittest.main()
