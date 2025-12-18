<script module lang="ts">
	export { default as BaseExample } from './Example.svelte';
</script>

<script lang="ts">
	import './app.css';
	import { Gradio } from '@gradio/utils';
	import { LogChannel, WebViewer, type Panel, type PanelState } from '@rerun-io/web-viewer';
	import { onMount } from 'svelte';
	import { Block } from '@gradio/atoms';
	import { StatusTracker } from '@gradio/statustracker';
	import type { FileData } from '@gradio/client';

	import type { SelectionChangeItem } from '@rerun-io/web-viewer';

	interface BinaryStream {
		url: string;
		is_stream: boolean;
	}

	interface RerunEvents {
		change: never;
		upload: never;
		clear: never;
		selection_change: SelectionChangeItem[];
		time_update: number;
		timeline_change: { timeline: string; time: number };
	}

	interface RerunProps {
		value: null | BinaryStream | (FileData | string)[];
		height: number | string;
		streaming: boolean;
		panel_states: { [K in Panel]: PanelState } | null;
	}

	class RerunGradio extends Gradio<RerunEvents, RerunProps> {}

	const props = $props();
	const gradio = new RerunGradio(props);

	let rr: WebViewer;
	let channel: LogChannel;
	let ref = $state<HTMLDivElement>();
	let dragging = $state(false);

	/**
	 * Used to keep track of the playlist currently being fetched
	 * in case we're streaming data.
	 */
	let current_playlist: { url: string; content: string } | null = null;

	$effect(() => {
		const h = gradio.props.height;
		gradio.props.height = typeof h === 'number' ? `${h}px` : h;
	});

	/** Fetch a list of segment URLs */
	async function fetch_playlist(value: BinaryStream) {
		let resp = await fetch(value.url);
		if (!resp.ok) throw new Error('Failed to fetch playlist');

		let baseUrl = new URL('./', value.url);
		let playlist = await resp.text();

		if (current_playlist && current_playlist.url == baseUrl.href) {
			// we're fetching the same playlist as last time
			// diff it and fetch only the segments we haven't seen yet
			let current_length = current_playlist.content.length;
			current_playlist.content = playlist;
			playlist = playlist.slice(current_length);
		} else {
			// it's a different playlist, start over
			current_playlist = { url: baseUrl.href, content: playlist };
		}

		// Each line is either a comment starting with #, a segment ID, or a segment URL.
		let urls: string[] = [];
		for (const line of playlist.trim().split('\n')) {
			if (line.startsWith('#') || line.trim().length === 0) continue;

			let url = line.startsWith('http') ? line : new URL(line, baseUrl).href;
			urls.push(url);
		}

		// Fetch each segment sequentially, and send them through the channel
		for (const url of urls) {
			let resp = await fetch(url);
			if (!resp.ok) throw new Error(`Failed to fetch segment: ${url}`);

			let bytes = await resp.arrayBuffer();
			channel.send_rrd(new Uint8Array(bytes));
		}
	}

	async function try_load_value(value: RerunProps['value'] = gradio.props.value) {
		if (value == null) {
			return;
		}

		if (rr == undefined || !rr.ready) {
			return;
		}

		// List of static or dynamic rrd URLs.
		// We just let the Viewer handle the streaming.
		if (Array.isArray(value)) {
			for (const file of value) {
				if (typeof file !== 'string') {
					if (file.url) {
						// fetch the file as a blob and send it to the viewer, over the channel
						let resp = await fetch(file.url);
						if (!resp.ok) {
							console.error('Failed to fetch file:', file.url);
							continue;
						}

						let bytes = await resp.bytes();

						channel.send_rrd(bytes);
					}
				} else {
					rr.open(file);
				}
			}
			return;
		}

		// Binary stream data. We receive a "playlist" of "typescript files",
		// each of which is a segment of the recording, produced by the backend
		// and streamed to us.
		if (value.is_stream) {
			await fetch_playlist(value);
			return;
		}

		// Binary data, but not streamed
		// TODO(jan, gijs): is this still a valid case?
		rr.open(value.url);
	}

	const is_panel = (v: string): v is Panel => ['top', 'blueprint', 'selection', 'time'].includes(v);

	function setup_panels(panel_states: RerunProps['panel_states'] = gradio.props.panel_states) {
		if (rr?.ready && panel_states) {
			for (const panel in panel_states) {
				if (!is_panel(panel)) continue;
				rr.override_panel_state(panel, panel_states[panel]);
			}
		}
	}

	onMount(() => {
		console.log('Rerun component mounted, gradio:', gradio);
		rr = new WebViewer();
		rr.on('ready', () => {
			console.log('Rerun viewer ready');
			channel = rr.open_channel('gradio');
			try_load_value();
			setup_panels();
			// Clear loading status when viewer is ready
			gradio.dispatch('clear_status', gradio.shared.loading_status);
		});
		rr.on('fullscreen', (on) => rr.toggle_panel_overrides(!on));

		rr._on_raw_event((event: string) => {
			const { type } = JSON.parse(event);
			gradio.dispatch(type, event);
		});

		rr.start(undefined, ref, {
			hide_welcome_screen: true,
			allow_fullscreen: true,
			width: '',
			height: ''
		});
		return () => {
			channel = null;
			rr.stop();
		};
	});

	// Watch for value changes
	$effect(() => {
		const value = gradio.props.value;
		try_load_value(value);
	});

	// Watch for panel_states changes
	$effect(() => {
		const panel_states = gradio.props.panel_states;
		setup_panels(panel_states);
	});
</script>

{#if !gradio.shared.interactive}
	<Block
		visible={gradio.shared.visible}
		variant="solid"
		border_mode={dragging ? 'focus' : 'base'}
		padding={false}
		elem_id={gradio.shared.elem_id}
		elem_classes={gradio.shared.elem_classes}
		allow_overflow={false}
		container={gradio.shared.container}
		scale={gradio.shared.scale}
		min_width={gradio.shared.min_width}
	>
		{#if !gradio.props.streaming}
			<StatusTracker
				autoscroll={gradio.shared.autoscroll}
				i18n={gradio.i18n}
				{...gradio.shared.loading_status}
				on_clear_status={() => gradio.dispatch('clear_status', gradio.shared.loading_status)}
			/>
		{/if}

		<div class="viewer" bind:this={ref} style:height={gradio.props.height}></div>
	</Block>
{/if}

<style lang="scss">
	div.viewer {
		width: 100%;
		:global(> canvas) {
			display: block;
			width: 100%;
			height: 100%;
		}
	}
</style>
