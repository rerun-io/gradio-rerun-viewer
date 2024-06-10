<svelte:options accessors={true} />

<script context="module" lang="ts">
  export { default as BaseExample } from "./Example.svelte";
</script>

<script lang="ts">
  import "./app.css";
  import type { Gradio } from "@gradio/utils";

  import { WebViewer, LogChannel } from "@rerun-io/web-viewer";
  import { onMount } from "svelte";

  import { Block } from "@gradio/atoms";
  import { StatusTracker } from "@gradio/statustracker";
  import type { FileData } from "@gradio/client";
  import type { LoadingStatus } from "@gradio/statustracker";

  interface BinaryStream {
    url: string;
    is_stream: boolean;
  }

  export let foo: string | null = null;
  export let elem_id = "";
  export let elem_classes: string[] = [];
  export let visible = true;
  export let height: number | string = 640;
  export let value: null | BinaryStream | (FileData | string)[] = null;
  export let container = true;
  export let scale: number | null = null;
  export let min_width: number | undefined = undefined;
  export let loading_status: LoadingStatus;
  export let interactive: boolean;
  export let streaming: boolean;

  let old_value: null | BinaryStream | (FileData | string)[] = null;

  export let gradio: Gradio<{
    change: never;
    upload: never;
    clear: never;
    clear_status: LoadingStatus;
  }>;

  $: height = typeof height === "number" ? `${height}px` : height;

  let dragging: boolean;
  let rr: WebViewer;
  let ref: HTMLDivElement;
  let patched_loading_status: LoadingStatus;

  function try_load_value() {
    if (
      JSON.stringify(value) !== JSON.stringify(old_value) &&
      rr != undefined &&
      rr.ready
    ) {
      old_value = value;
      if (!Array.isArray(value)) {
        if (value.is_stream) {
          rr.open(value.url, { follow_if_http: true });
        } else {
          rr.open(value.url);
        }
      } else {
        for (const file of value) {
          if (typeof file !== "string") {
            if (file.url) {
              rr.open(file.url);
            }
          } else {
            rr.open(file);
          }
        }
      }
    }
  }

  onMount(() => {
    rr = new WebViewer();
    rr.start(undefined, ref, true).then(() => {
      try_load_value();
    });

    return () => {
      rr.stop();
    };
  });

  $: {
    patched_loading_status = loading_status;

    // In streaming mode, we want the UI to be interactive even while the model is generating
    // so set the status to complete.
    if (streaming && patched_loading_status?.status === "generating") {
      patched_loading_status.status = "complete";
    }
  }

  $: value, try_load_value();
</script>

{#if !interactive}
  <Block
    {visible}
    variant={"solid"}
    border_mode={dragging ? "focus" : "base"}
    padding={false}
    {elem_id}
    {elem_classes}
    allow_overflow={false}
    {container}
    {scale}
    {min_width}
  >
    <h3>{foo}</h3>
    <StatusTracker
      autoscroll={gradio.autoscroll}
      i18n={gradio.i18n}
      {...patched_loading_status}
      on:clear_status={() => gradio.dispatch("clear_status", loading_status)}
    />
    <div class="viewer" bind:this={ref} style:height />
  </Block>
{/if}

<style lang="scss">
  div.viewer {
    width: 100%;

    :global(> canvas) {
      position: initial !important;
      top: unset !important;
      width: 100%;
      height: 100%;
    }
  }
</style>
