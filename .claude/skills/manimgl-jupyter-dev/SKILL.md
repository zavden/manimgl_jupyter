---
name: manimgl-jupyter-dev
description: Internals of manimgl_jupyter.py and how to change or test it. Use when editing the module, debugging the %%manim magic itself, running or extending the kernel-based tests, or checking that a new manimlib version still provides what the module relies on (config builder, Scene constructor, SceneFileWriter attributes).
---

# Working on manimgl_jupyter

One module, `manimgl_jupyter.py`, read top to bottom:

1. **argv guard**: saves `sys.argv`, sets it to `["manimgl"]`, imports `manimlib`
   (`from manimlib import *`), restores it. Everything else comes after.
2. **`jupyter_config`**: a `JupyterConfig` dataclass with `slots`, so a typo in a
   field name raises instead of silently creating one.
3. **`split_flags` / `build_config`**: the magic line is split with `shlex`
   (backslashes preserved on Windows) and parsed by manimlib's own parser:
   `manimlib.config.initialize_manim_config()` with `sys.argv` set to
   `["manimgl", "-w", *flags]`. `-w` makes it a file render with no window. The
   first positional, which the parser takes for a file, is moved to the scene names.
4. **Scene selection**: `_scene_classes_in` parses the cell with `ast` for top-level
   class definitions, then keeps `Scene` subclasses whose `__module__` is `__main__`.
5. **`_render`**: `SceneClass(**config.scene, camera_config=config.camera,
   file_writer_config=config.file_writer)` then `scene.run()`. No window means
   `Camera` creates its own offscreen wgpu device. With `--prerun`, `_count_frames`
   does the dry run first. On any exception `_abandon` closes the ffmpeg pipe so no
   process is left waiting, then re-raises.
6. **`show_media`**: builds `<video>` or `<img>` HTML, base64 data URI when
   `media_embed`, else a relative link with `?v=<mtime>` to defeat caching.
7. **`ManimglMagics`**: `%%manim` runs the cell through `shell.run_cell` (so
   tracebacks and IPython syntax work as in a normal cell), stops on failure, then
   renders and shows each selected scene. `%%manimgl` is an alias.
8. **Registration**: `load_ipython_extension` for `%load_ext`, and automatic
   registration on import when an IPython shell exists.

## Invariants to keep

- The argv guard must run before manimlib's first import, so the module stays a
  top-level module. Inside `manimlib/` it would be too late: the package
  `__init__` imports `manimlib.config` first.
- Flags are parsed by manimlib, never re-implemented. New CLI flags work for free.
- No edits to manimlib. The global `manim_config` is left as built; per-render
  settings go in as `camera_config` and `file_writer_config` overrides, which
  `Scene.__init__` merges over the global ones.
- Output is HTML with embedded data by default. VSCode's notebook renderer cannot
  load local files by path.

## manimlib internals relied on

Check these when manimlib updates:

- `manimlib.config.initialize_manim_config()` returning an `addict.Dict` with
  `.scene`, `.camera`, `.file_writer` and `.run` (`.scene_names`, `.file_name`,
  `.write_all`, `.prerun`); it must read `sys.argv` when called.
- `Scene.__init__` accepting `**config.scene` plus `camera_config` and
  `file_writer_config`; `Scene.run()`; `scene.time` and `scene.skip_time`.
- `scene.file_writer` with `write_to_movie`, `save_last_frame`,
  `get_movie_file_path()`, `get_image_file_path()`, `writing_process`,
  `progress_display`.
- `Camera(window=None)` building an offscreen GPU device.
- `addict.Dict` (a manimgl dependency, listed in pyproject too).

## Testing

```bash
pip install -e .[test]
pytest
```

`tests/test_notebook.py` starts a real ipykernel with `--f={connection_file}`,
the form VSCode uses, with the repo root on `PYTHONPATH`, and runs cells through
`jupyter_client`. It needs a GPU wgpu can drive and ffmpeg, like manimgl itself,
and takes about a minute. One test asserts that a plain `import manimlib` still
fails in such a kernel; if it ever passes, manimlib fixed its argv handling.

Quick manual checks without a kernel:

```bash
python -c "import sys; sys.argv=['k','--f=/x.json']; import manimgl_jupyter; print('ok')"
python -c "import manimgl_jupyter as m; print(m.build_config(['-l','--fps','15','S']).camera)"
```

To run cells by hand, copy the `Kernel` class from the tests; its `run(code)`
returns the execute reply and the iopub messages, where `display_data` with
`text/html` holds the rendered output.

## Releasing

Bump `version` in `pyproject.toml` and `__version__` in the module together.
`pip wheel . --no-deps` must produce a wheel holding `manimgl_jupyter.py` only.
