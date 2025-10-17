import tailwindcss from '@tailwindcss/vite';
import wasm from 'vite-plugin-wasm';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { searchForWorkspaceRoot } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// `@rerun-io/web-viewer` uses `new URL("./re_viewer_bg.wasm", import.meta.url)` since 0.17,
// which does not play well with `vite dev`: https://github.com/rerun-io/rerun/issues/6815
// we need to patch the config, but `gradio` does not let us directly set the `optimize` option.
/** @type {() => import("vite").Plugin} */
const hack = () => ({
	config() {
		return {
			optimizeDeps: {
				exclude: process.env.NODE_ENV === 'production' ? [] : ['@rerun-io/web-viewer']
			},
			server: {
				fs: {
					allow: [
						searchForWorkspaceRoot(process.cwd()),
						// NOTE: hack to allow `new URL("file://...")` in `web-viewer` when it is a linked package
						fs.realpathSync(path.join(__dirname, 'node_modules', '@rerun-io/web-viewer'))
					]
				}
			}
		};
	}
});

export default {
	plugins: [wasm(), tailwindcss(), hack()],
	svelte: {
		preprocess: []
	},
	build: {
		target: 'esnext'
	}
};
