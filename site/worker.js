// Runs the Python randomizer in Pyodide, off the main thread.
// Messages in:  {type: 'nup', file} | {type: 'generate', options}
// Messages out: {type: 'status', text} | {type: 'ready', items}
//               {type: 'nup', result} | {type: 'done', name, bytes, seed}
//               {type: 'error', message}
import { loadPyodide } from 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs';

let py = null;
let call = null;
let nupName = null;
const NUP_DIR = '/nup';

function status(text) { postMessage({ type: 'status', text }); }

async function init() {
  status('Loading Python…');
  py = await loadPyodide({ indexURL: 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/' });
  status('Loading the randomizer…');
  const resp = await fetch('randomizer.zip', { cache: 'no-cache' });
  if (!resp.ok) throw new Error('Could not download the randomizer (' + resp.status + ').');
  py.unpackArchive(await resp.arrayBuffer(), 'zip', { extractDir: '/rando' });
  py.runPython("import sys; sys.path.insert(0, '/rando')");
  call = py.pyimport('randomizer.browser').call;
  py.FS.mkdir(NUP_DIR);
  postMessage({ type: 'ready', items: JSON.parse(call('items')) });
}

function api(name, args) {
  return JSON.parse(call(name, JSON.stringify(args || [])));
}

function mountNup(file) {
  if (nupName !== null) py.FS.unmount(NUP_DIR);
  // WORKERFS reads the File lazily, in slices: the game is never loaded whole.
  py.FS.mount(py.FS.filesystems.WORKERFS, { files: [file] }, NUP_DIR);
  nupName = file.name;
}

const ready = init().catch((e) => {
  postMessage({ type: 'error', message: 'Could not start the randomizer: ' + (e.message || e) });
  throw e;
});

onmessage = async (ev) => {
  const msg = ev.data;
  try {
    await ready;
    if (msg.type === 'nup') {
      status('Checking the game file…');
      mountNup(msg.file);
      postMessage({ type: 'nup', result: api('check_nup', [NUP_DIR + '/' + nupName]) });
    } else if (msg.type === 'generate') {
      if (nupName === null) throw new Error('Choose the game file first.');
      status('Generating the seed… (this takes a few seconds)');
      const r = api('generate_zip', [NUP_DIR + '/' + nupName, msg.options]);
      if (!r.ok) { postMessage({ type: 'error', message: r.error }); return; }
      const bytes = py.FS.readFile(r.zip_path);
      py.FS.unlink(r.zip_path);
      postMessage({ type: 'done', name: r.zip_name, seed: r.seed, bytes }, [bytes.buffer]);
    }
  } catch (e) {
    postMessage({ type: 'error', message: String(e && e.message ? e.message : e) });
  }
};
