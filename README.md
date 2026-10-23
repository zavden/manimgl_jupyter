# manimgl_jupyter

ManimGL inside Jupyter notebooks, VSCode included, with a `%%manim` cell magic in the style of ManimCE.

```python
from manimgl_jupyter import *
```

```python
%%manim -l HelloManimGL
class HelloManimGL(Scene):
    def construct(self):
        self.play(Write(Text("ManimGL in a notebook")))
```

The cell renders the scene to a file, with no window, and shows the video right under it.

*En español: [README.es.md](README.es.md)*

## Why this exists

Two things keep ManimGL out of notebooks:

1. `manimlib` parses `sys.argv` the moment it is imported. A Jupyter kernel is started with arguments manimgl's parser does not know, and VSCode in particular passes `--f=<connection file>`, which argparse rejects as ambiguous (`--fps`, `--finder`, `--file_name`, `--full_screen`). `from manimlib import *` dies with `SystemExit: 2` before you can do anything.
2. `manimgl` renders to a window or to a file from the command line. Nothing shows a result inside a notebook.

`manimgl_jupyter` fixes both without changing a line of manimlib. It is one module.

## Requirements

- Python 3.10 or newer.
- A recent **ManimGL from GitHub**, installed and working from the command line (`manimgl example_scenes.py OpeningManimExample -w`). The module uses manimlib's `manim_config` based configuration, which the PyPI release `manimgl 1.7.2` predates, so install manimgl from its repository (or your fork) first.
- Whatever manimgl needs: `ffmpeg` on the PATH, LaTeX for `Tex`, a GPU driver wgpu can use (Vulkan, Metal or DirectX 12).

## Install

Into the same environment that has manimgl:

```bash
pip install git+https://github.com/YOUR-USER/manimgl_jupyter.git
```

or clone the repository and run `pip install -e .` in it. The install also brings `ipykernel` and `ipywidgets`, so the environment can serve as a notebook kernel and the progress bar renders as a widget.

In VSCode, open an `.ipynb` and pick that environment's interpreter as the kernel. To see the kernel from notebooks in any folder, register it once:

```bash
python -m ipykernel install --user --name manimgl
```

## Usage

### Cell magic

```python
%%manim -l SceneName
class SceneName(Scene):
    def construct(self):
        ...
```

The cell body is ordinary Python and runs in the notebook namespace first, so helper functions and constants defined there stay available to later cells. Then the named scene is rendered and displayed. `%%manimgl` is an alias of `%%manim`.

### Line magic

```python
%manim -s SceneName
```

renders a scene defined in an earlier cell.

### Which scenes

- With names on the line, those scenes.
- With no name, every `Scene` subclass the cell defines, in order.
- With `-a`, every scene defined in the notebook so far.

### Flags

They are the flags of the `manimgl` command, parsed by manimgl itself. The common ones:

| Flag | Effect |
|---|---|
| `-l` `-m` `--hd` `--uhd` | 854x480, 1280x720, 1920x1080, 3840x2160 |
| `-r 1280x720` | any resolution |
| `--fps 60` | frame rate |
| `-s` | skip the animations, save the last frame as PNG |
| `-i` | write a GIF |
| `-t` | transparent background, `.mov` with ProRes (see Notes) |
| `-c "#112233"` | background color |
| `-n 3` or `-n 3,6` | start at animation 3, or render animations 3 to 6 |
| `-a` | render every scene |
| `--prerun` | dry run first, so the progress bar has a total |
| `--file_name NAME`, `--video_dir DIR` | output name and folder |
| `-q` | no progress bar, no "File ready" line |

`%manim -h` prints the full list. Rendering in a notebook always writes to file; no window opens, and window-only features (`self.embed()`, `-p`, interactive mode) do nothing.

### Output

Files go where `manimgl -w` puts them: `videos/` next to the notebook (the kernel's working directory), or wherever `custom_config.yml` in that directory says. The result is embedded base64 in the cell output.

```python
jupyter_config.media_width = "100%"    # CSS max-width of what is shown, default "60%"
jupyter_config.media_embed = False     # link the file instead of embedding it
jupyter_config.video_attributes = "controls loop"   # default "controls autoplay loop"
```

Embedding is what VSCode needs, since its notebook renderer cannot load local files. Linking keeps the `.ipynb` small and suits JupyterLab.

### From Python

```python
path = render_scene(SceneName, "-l --fps 24")   # the Path written, nothing displayed
show_media(path)
```

### As an IPython extension

`%load_ext manimgl_jupyter` registers the magic as well. It must still run before any import of `manimlib`, for the reason above.

## How it works

1. **Import.** The module saves `sys.argv`, sets it to `["manimgl"]`, imports `manimlib` (re-exporting all its names), and restores it. manimlib builds its global configuration as if run with no arguments.
2. **The cell.** `%%manim` runs the cell body through IPython, so classes land in the notebook namespace and errors show as usual. If the body fails, nothing is rendered.
3. **The flags.** The line is handed to manimlib's own parser by calling `manimlib.config.initialize_manim_config()` with `sys.argv` set to `manimgl -w <flags>`. The result is the exact configuration the command line would use, with `-w` making it a file render and no window. The first positional, which the parser takes for a file, is a scene name here.
4. **The render.** The scene class is instantiated with that configuration (`camera_config` and `file_writer_config` passed explicitly, so the global configuration is left alone) and `scene.run()` is called. Without a window, manimlib's `Camera` creates its own offscreen wgpu device, and `SceneFileWriter` pipes frames to ffmpeg. With `--prerun`, a skipped dry run first counts the frames for the progress bar.
5. **The display.** The resulting mp4, PNG or GIF is read and embedded as a base64 data URI in a `<video>` or `<img>` element. With `media_embed = False` it is linked relative to the notebook, with the file's modification time as a cache buster.
6. **Errors.** If the scene raises, the ffmpeg pipe is closed so no process is left waiting on it, and the exception propagates to the cell.

## Structure

```
manimgl_jupyter/
├── manimgl_jupyter.py        the module: argv guard, config builder, renderer, display, magic
├── pyproject.toml            packaging; installs the module as a single top-level file
├── examples/demo.ipynb       a notebook to try it
├── tests/test_notebook.py    end-to-end tests through a real kernel launched like VSCode does
├── .claude/skills/           Claude Code skills, see below
├── README.md, README.es.md
└── LICENSE
```

Inside the module, top to bottom: the argv guard and imports; `jupyter_config`; `split_flags` and `build_config`; scene discovery (`_scene_classes_in`); `render_scene` / `_render`; `show_media`; the `ManimglMagics` class; registration (`load_ipython_extension` and auto-registration on import).

## Notes and limits

- `-t` writes a `.mov` with ProRes, which browsers cannot play; the path is logged instead of a player.
- GIFs are large when embedded. Prefer mp4 unless a GIF is what you need.
- Embedded media makes the `.ipynb` grow. Clear outputs before committing notebooks, or use `media_embed = False` where linked files display.
- Each render creates its own GPU device and compiles the shaders again; that is a fraction of a second. LaTeX and text are cached on disk by manimlib.
- If a scene raises part way, a `SceneName_temp.mp4` is left behind, as with the command line. Interrupting the kernel keeps and shows the partial video.
- Tested on Linux. Nothing in the module is platform specific; on Windows, backslashes in paths passed as flags are preserved.

## Claude Code skills

`.claude/skills/` holds three skills in the [Agent Skills](https://agentskills.io) format, picked up automatically by Claude Code when working in this repository. Copy a folder to `~/.claude/skills/` to use it anywhere.

| Skill | For |
|---|---|
| `manimgl-notebook` | rendering scenes in notebooks: flags, output, display settings, troubleshooting |
| `manimgl-vs-manimce` | the ManimGL API and its differences from ManimCE, so scenes are written against the right names |
| `manimgl-jupyter-dev` | how the module works inside, what it relies on in manimlib, how to test it |

## Development

```bash
pip install -e .[test]
pytest
```

The tests start a real ipykernel with `--f=<connection file>`, the launch form VSCode uses, and run cells through it with the repository root on `PYTHONPATH`. They need a GPU and ffmpeg, like manimgl, and take about a minute.

## License

MIT.
