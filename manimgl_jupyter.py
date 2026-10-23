"""
ManimGL inside Jupyter notebooks (VSCode, JupyterLab, ...), in the style of ManimCE.

Import it instead of ``manimlib`` and you get every manimlib name plus a
``%%manim`` cell magic (``%%manimgl`` is an alias) that renders a scene and shows
the resulting video or image right under the cell::

    from manimgl_jupyter import *

    %%manim -l MyScene
    class MyScene(Scene):
        def construct(self):
            self.play(Write(Text("Hello")))

The magic takes the same flags as the ``manimgl`` command (``-l``, ``-m``,
``--hd``, ``-s``, ``-i``, ``-t``, ``-r 1280x720``, ``--fps 60``, ``-c BLACK``,
``-n 2,5``, ``--prerun``, ...; ``%manim -h`` lists them). It always writes to
file, there is no window. Files go where ``manimgl -w`` would put them: the
``videos`` folder next to the notebook, or wherever ``custom_config.yml`` says.

* No scene name: every Scene subclass the cell defines gets rendered.
* Line form, ``%manim -s MyScene``, renders a scene defined in an earlier cell.
* ``jupyter_config.media_width = "100%"`` sets the size of what is shown, and
  ``jupyter_config.media_embed = False`` links the file instead of embedding it
  base64 in the notebook (smaller .ipynb, but VSCode cannot show linked files).

Why a module of its own rather than ``from manimlib import *``: manimlib reads
``sys.argv`` the moment it is imported, and a Jupyter kernel is started with
arguments manimgl's parser rejects (VSCode passes ``--f=<connection file>``,
ambiguous with ``--fps``/``--finder``/...). This module hides them during the
import, so it must be imported before, or instead of, manimlib.
"""
from __future__ import annotations

import ast
import base64
import copy
import inspect
import mimetypes
import os
import shlex
import sys
import warnings
from dataclasses import dataclass
from addict import Dict
from pathlib import Path

# tqdm, as it is imported by manimlib, complains when ipywidgets is missing and
# it has to fall back to a text progress bar. The fallback is fine.
warnings.filterwarnings("ignore", message=r"IProgress not found")

# manimlib builds its global configuration from sys.argv on import, see
# manimlib.config.initialize_manim_config. Hide the kernel's arguments meanwhile.
_kernel_argv = sys.argv
sys.argv = ["manimgl"]
try:
    import manimlib
    from manimlib import *
finally:
    sys.argv = _kernel_argv

import manimlib.config
from manimlib.logger import log
from manimlib.scene.scene import Scene

from IPython import get_ipython
from IPython.core.error import UsageError
from IPython.core.magic import Magics, line_cell_magic, magics_class
from IPython.display import HTML, display

__version__ = "0.1.0"

__all__ = [
    *(name for name in dir(manimlib) if not name.startswith("_")),
    "jupyter_config",
    "render_scene",
    "ManimglMagics",
]


@dataclass(slots=True)
class JupyterConfig:
    # CSS max-width of the video or image shown under the cell
    media_width: str = "60%"
    # Embed the file base64 in the output (needed in VSCode) or link to it
    media_embed: bool = True
    # Attributes of the <video> tag
    video_attributes: str = "controls autoplay loop"


jupyter_config = JupyterConfig()

# What a browser can show; anything else (a transparent .mov, say) is only named
_SHOWABLE = {".mp4", ".webm", ".gif", ".png", ".jpg", ".jpeg"}


def split_flags(line: str) -> list[str]:
    """Split a magic line into arguments, keeping the backslashes of Windows paths."""
    if os.name == "nt":
        line = line.replace("\\", "\\\\")
    return shlex.split(line)


def build_config(flags: list[str]):
    """
    The configuration ``manimgl -w <flags>`` would run with, built by manimlib's
    own parser so every CLI flag means the same here.
    """
    saved_argv = sys.argv
    sys.argv = ["manimgl", "-w", *flags]
    try:
        config = manimlib.config.initialize_manim_config()
    finally:
        sys.argv = saved_argv
    # There is no file argument in a notebook, so the first positional, which the
    # parser takes for one, is really a scene name
    run = config.run
    if run.file_name:
        run.scene_names = [run.file_name, *run.scene_names]
        run.file_name = None
    return config


def _is_scene_class(obj) -> bool:
    return (
        inspect.isclass(obj)
        and issubclass(obj, Scene)
        and obj.__module__ == "__main__"
    )


def _scene_classes_in(cell: str | None, namespace: dict) -> list[type]:
    """
    The Scene subclasses a cell defines, in order; or, with no cell, every one
    defined in the notebook so far.
    """
    if cell is None:
        names = list(namespace)
    else:
        try:
            names = [
                node.name for node in ast.parse(cell).body
                if isinstance(node, ast.ClassDef)
            ]
        except SyntaxError:
            names = []
    return [namespace[name] for name in names if _is_scene_class(namespace.get(name))]


def _count_frames(scene_class, scene_config, fps: int) -> int:
    """A dry run of the scene, to give the progress bar a total (``--prerun``)."""
    pre_config = copy.deepcopy(scene_config)
    pre_config.file_writer_config.update(
        write_to_movie=False, save_last_frame=False, quiet=True,
    )
    pre_config.skip_animations = True
    pre_scene = scene_class(**pre_config)
    pre_scene.run()
    return int((pre_scene.time - pre_scene.skip_time) * fps)


def _abandon(scene) -> None:
    """After an error mid-render, leave no ffmpeg waiting on the pipe."""
    file_writer = scene.file_writer
    process = getattr(file_writer, "writing_process", None)
    if process is not None and process.poll() is None:
        process.stdin.close()
        process.wait()
    if file_writer.progress_display is not None:
        file_writer.progress_display.close()


def render_scene(scene_class, flags: str | list[str] = "") -> Path | None:
    """
    Render ``scene_class`` to file as ``manimgl -w <flags>`` would, and return
    the path of the movie or image written, if one was.
    """
    if isinstance(flags, str):
        flags = split_flags(flags)
    config = build_config(flags)
    return _render(scene_class, config)


def _render(scene_class, config) -> Path | None:
    scene_config = Dict(config.scene)
    scene_config.update(
        camera_config=config.camera,
        file_writer_config=config.file_writer,
    )
    if config.file_writer.write_to_movie and config.run.prerun:
        scene_config.file_writer_config.total_frames = _count_frames(
            scene_class, scene_config, config.camera.fps
        )

    scene = scene_class(**scene_config)
    try:
        scene.run()
    except BaseException:
        _abandon(scene)
        raise

    file_writer = scene.file_writer
    if file_writer.write_to_movie:
        return Path(file_writer.get_movie_file_path())
    if file_writer.save_last_frame:
        return Path(file_writer.get_image_file_path())
    return None


def show_media(path: Path) -> None:
    """Display a rendered movie or image under the current cell."""
    path = Path(path)
    if not path.is_file() or path.suffix.lower() not in _SHOWABLE:
        log.info(f"Not shown in the notebook, see {path}")
        return

    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if jupyter_config.media_embed:
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        src = f"data:{mime};base64,{data}"
    else:
        # The modification time keeps the browser from showing a cached
        # earlier render of a scene with the same name
        try:
            link = Path(os.path.relpath(path))
        except ValueError:  # another drive on Windows
            link = path.resolve()
        src = f"{link.as_posix()}?v={int(path.stat().st_mtime)}"

    style = f'style="max-width: {jupyter_config.media_width};"'
    if mime.startswith("image/"):
        html = f'<img src="{src}" {style}>'
    else:
        html = (
            f'<video src="{src}" type="{mime}" {jupyter_config.video_attributes} {style}>'
            "</video>"
        )
    display(HTML(html))


@magics_class
class ManimglMagics(Magics):
    @line_cell_magic
    def manim(self, line: str, cell: str | None = None):
        """
        Render ManimGL scenes from a notebook.

            %%manim [manimgl flags] [SceneName ...]
            class SceneName(Scene): ...

            %manim [manimgl flags] SceneName

        Flags are those of the manimgl command, see ``%manim -h``.
        """
        if cell is not None:
            result = self.shell.run_cell(cell, store_history=False)
            if not result.success:
                return

        try:
            config = build_config(split_flags(line))
        except SystemExit:
            # argparse has already printed its help or complaint
            return

        namespace = self.shell.user_ns
        run_config = config.run
        if run_config.scene_names and not run_config.write_all:
            scene_classes = []
            for name in run_config.scene_names:
                scene_class = namespace.get(name)
                if not _is_scene_class(scene_class):
                    known = ", ".join(c.__name__ for c in _scene_classes_in(None, namespace))
                    raise UsageError(
                        f"No Scene class named {name!r} has been defined in this notebook"
                        + (f"; known scenes: {known}" if known else "")
                    )
                scene_classes.append(scene_class)
        else:
            scene_classes = _scene_classes_in(cell, namespace)
            if not scene_classes:
                raise UsageError(
                    "No Scene class to render: define one in the cell, "
                    "or name one, e.g. %%manim -l MyScene"
                )

        for scene_class in scene_classes:
            path = _render(scene_class, config)
            if path is not None:
                show_media(path)

    @line_cell_magic("manimgl")
    def manimgl(self, line: str, cell: str | None = None):
        """Alias of %%manim."""
        return self.manim(line, cell)


def load_ipython_extension(ipython) -> None:
    """Lets ``%load_ext manimgl_jupyter`` register the magic as well."""
    ipython.register_magics(ManimglMagics)


_ipython = get_ipython()
if _ipython is not None:
    load_ipython_extension(_ipython)
