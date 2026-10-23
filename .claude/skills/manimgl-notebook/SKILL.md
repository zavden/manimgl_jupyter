---
name: manimgl-notebook
description: Render ManimGL scenes inside Jupyter or VSCode notebooks with the %%manim magic from manimgl_jupyter. Use when writing, running or debugging a notebook cell that renders a manimgl Scene, choosing flags (-l -m --hd -s -i -t -r --fps -c -n -a --prerun), sizing or embedding the output, or when `from manimlib import *` fails in a kernel with SystemExit 2 or "ambiguous option --f".
---

# Rendering ManimGL in a notebook

## Setup cell, once per kernel

```python
from manimgl_jupyter import *
```

This gives every `manimlib` name plus the `%%manim` magic (alias `%%manimgl`). It
must come before any import of `manimlib`: manimlib parses `sys.argv` on import
and the kernel's arguments (VSCode passes `--f=<file>`) make it exit with
`SystemExit: 2`. If that already happened, restart the kernel and import
`manimgl_jupyter` first. `%load_ext manimgl_jupyter` works too, under the same rule.

## Render cell

```python
%%manim -l SceneName
class SceneName(Scene):
    def construct(self):
        ...
```

- The cell body is ordinary Python, run in the notebook namespace first. Helper
  functions and constants defined in it stay available to later cells.
- Scene names are optional. Without one, every `Scene` subclass defined in the
  cell is rendered, in order. `-a` renders every scene defined so far.
- Line form `%manim -s SceneName` renders a scene defined in an earlier cell.
- It always writes to file. No window opens; `self.embed()`, `-p` and the
  interactive features are no-ops.
- One render per cell is the natural unit. Keep `run_time` short while iterating
  and use `-l`; switch to `-m` or `--hd` for the final version.

## Flags, identical to the `manimgl` command

| Flag | Effect |
|---|---|
| `-l` `-m` `--hd` `--uhd` | 854x480, 1280x720, 1920x1080, 3840x2160 |
| `-r 1280x720` | any resolution |
| `--fps 60` | frame rate |
| `-s` | skip animations, save the last frame as PNG |
| `-i` | write a GIF |
| `-t` | transparent background, `.mov` ProRes; not shown inline, the path is logged |
| `-c "#112233"` | background color |
| `-n 3` or `-n 3,6` | start at animation 3, or render animations 3 to 6 |
| `-a` | render every scene (`--write_all`) |
| `--prerun` | dry run first so the progress bar has a total |
| `--file_name NAME` `--video_dir DIR` | output name and folder |
| `-q` | no progress bar or "File ready" line |

`%manim -h` prints the full list. Paths with spaces go in quotes.

## Output

Files land where `manimgl -w` would put them: `videos/` next to the notebook
(the kernel's working directory), or what `custom_config.yml` in that directory
says. The result is embedded base64 in the cell output as `<video>` or `<img>`.

```python
jupyter_config.media_width = "100%"   # CSS max-width of what is shown, default "60%"
jupyter_config.media_embed = False    # link the file instead of embedding it
jupyter_config.video_attributes = "controls loop"  # default "controls autoplay loop"
```

VSCode cannot display linked local files, so keep `media_embed = True` there.
Linking suits JupyterLab and keeps the `.ipynb` small.

From Python instead of the magic:

```python
path = render_scene(SceneName, "-l --fps 24")   # returns the Path written, no display
show_media(path)
```

## Troubleshooting

- `SystemExit: 2` or `ambiguous option: --f=...` on import: manimlib was imported
  before `manimgl_jupyter`. Restart the kernel; import `manimgl_jupyter` first.
- `UsageError: No Scene class named 'X'`: the name is misspelled, the class is not
  a `Scene` subclass, or it was defined inside a function. Define scenes at the
  top level of a cell. The message lists the scenes it does know.
- Nothing shown, log says "Not shown in the notebook": the output is a `.mov`
  from `-t`; open the file from `videos/`.
- Video area empty in VSCode: `jupyter_config.media_embed` is `False`.
- An exception inside `construct` prints the usual traceback; a
  `SceneName_temp.mp4` is left behind, the same as the CLI. Fix and re-run.
- Interrupting the kernel mid-render keeps and shows the partial video.
- The first render after import is slower: a GPU device is created and shaders
  compiled per render; `Tex` and `Text` results are cached on disk by manimlib.
- `Tex` fails: LaTeX is not installed or not on the PATH. `Text` needs no LaTeX.
