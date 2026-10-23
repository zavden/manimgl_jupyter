"""
End-to-end tests through a real ipykernel, launched the way VSCode launches one
(``--f=<connection file>``), since that launch form is what breaks a plain
``import manimlib`` and what this package exists for.

They need what manimgl needs: a GPU wgpu can drive and ffmpeg on the PATH. The
kernel runs with the repository root on PYTHONPATH, so a fresh clone can be
tested without installing it first, as long as manimgl is installed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from jupyter_client.kernelspec import KernelSpec
from jupyter_client.manager import KernelManager

REPO = Path(__file__).resolve().parents[1]

DEFINE_DEMO = """
class Demo(Scene):
    def construct(self):
        self.play(FadeIn(Square(color=BLUE)), run_time=0.3)
"""


class Kernel:
    def __init__(self, workdir: Path):
        self.workdir = workdir
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            p for p in (str(REPO), env.get("PYTHONPATH")) if p
        )
        self.manager = KernelManager()
        self.manager._kernel_spec = KernelSpec(
            argv=[sys.executable, "-m", "ipykernel_launcher", "--f={connection_file}"],
            display_name="vscode-style",
            language="python",
        )
        self.manager.start_kernel(cwd=str(workdir), env=env)
        self.client = self.manager.client()
        self.client.start_channels()
        self.client.wait_for_ready(timeout=120)

    def run(self, code: str):
        """Execute a cell; return (reply content, iopub messages it produced)."""
        messages = []
        reply = self.client.execute_interactive(
            code, output_hook=messages.append, timeout=600
        )
        return reply["content"], messages

    def close(self):
        self.client.stop_channels()
        self.manager.shutdown_kernel(now=True)


def html_outputs(messages) -> list[str]:
    return [
        m["content"]["data"]["text/html"]
        for m in messages
        if m["header"]["msg_type"] == "display_data"
        and "text/html" in m["content"].get("data", {})
    ]


def stream_text(messages) -> str:
    return "".join(
        m["content"]["text"] for m in messages if m["header"]["msg_type"] == "stream"
    )


@pytest.fixture
def fresh_kernel(tmp_path):
    kernel = Kernel(tmp_path)
    yield kernel
    kernel.close()


@pytest.fixture(scope="module")
def kernel(tmp_path_factory):
    """A kernel with the module imported and a Demo scene defined."""
    kernel = Kernel(tmp_path_factory.mktemp("notebook"))
    reply, _ = kernel.run("from manimgl_jupyter import *")
    assert reply["status"] == "ok", reply
    reply, _ = kernel.run(DEFINE_DEMO)
    assert reply["status"] == "ok", reply
    yield kernel
    kernel.close()


def test_kernel_gets_the_vscode_launch_form(fresh_kernel):
    reply, messages = fresh_kernel.run("import sys; print(sys.argv[1])")
    assert reply["status"] == "ok"
    assert stream_text(messages).startswith("--f=")


def test_plain_manimlib_import_fails_in_such_a_kernel(fresh_kernel):
    # The reason this package exists. Should this start passing, manimlib has
    # stopped choking on the kernel's argv and the argv guard can go.
    reply, _ = fresh_kernel.run("import manimlib")
    assert reply["status"] == "error"
    assert reply["ename"] == "SystemExit"


def test_import_gives_manimlib_names_and_a_clean_config(fresh_kernel):
    reply, messages = fresh_kernel.run(
        "from manimgl_jupyter import *\n"
        "print(Scene.__name__, manim_config.run.file_name, "
        "manim_config.window.full_screen, type(jupyter_config).__name__)"
    )
    assert reply["status"] == "ok", reply
    assert stream_text(messages).split() == ["Scene", "None", "False", "JupyterConfig"]


def test_cell_magic_renders_and_embeds_the_video(kernel):
    reply, messages = kernel.run(
        "%%manim -l Quick\n"
        "class Quick(Scene):\n"
        "    def construct(self):\n"
        "        self.play(ShowCreation(Circle()), run_time=0.3)\n"
    )
    assert reply["status"] == "ok", reply
    assert (kernel.workdir / "videos" / "Quick.mp4").is_file()
    videos = [h for h in html_outputs(messages) if h.startswith("<video")]
    assert len(videos) == 1
    assert "data:video/mp4;base64," in videos[0]
    assert "max-width: 60%" in videos[0]


def test_cell_without_a_name_renders_the_scenes_it_defines(kernel):
    reply, messages = kernel.run(
        "%%manim -l\n"
        "class First(Scene):\n"
        "    def construct(self):\n"
        "        self.wait(0.1)\n"
        "class Second(Scene):\n"
        "    def construct(self):\n"
        "        self.wait(0.1)\n"
    )
    assert reply["status"] == "ok", reply
    assert len([h for h in html_outputs(messages) if h.startswith("<video")]) == 2
    assert (kernel.workdir / "videos" / "First.mp4").is_file()
    assert (kernel.workdir / "videos" / "Second.mp4").is_file()


def test_line_magic_saves_and_embeds_the_last_frame(kernel):
    reply, messages = kernel.run("%manim -s Demo")
    assert reply["status"] == "ok", reply
    assert (kernel.workdir / "videos" / "Demo.png").is_file()
    images = [h for h in html_outputs(messages) if h.startswith("<img")]
    assert len(images) == 1
    assert "data:image/png;base64," in images[0]


def test_gif_flag(kernel):
    reply, messages = kernel.run("%manim -l -i Demo")
    assert reply["status"] == "ok", reply
    assert (kernel.workdir / "videos" / "Demo.gif").is_file()
    assert any("data:image/gif;base64," in h for h in html_outputs(messages))


def test_unknown_scene_is_a_usage_error(kernel):
    reply, _ = kernel.run("%manim -l Nope")
    assert reply["status"] == "error"
    assert reply["ename"] == "UsageError"
    assert "Nope" in reply["evalue"] and "Demo" in reply["evalue"]


def test_help_prints_manimgl_usage(kernel):
    reply, messages = kernel.run("%manim -h")
    assert reply["status"] == "ok", reply
    assert "usage:" in stream_text(messages)


@pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe not on PATH")
def test_resolution_and_fps_flags_reach_the_file(kernel):
    reply, _ = kernel.run("%manim -r 640x360 --fps 15 Demo")
    assert reply["status"] == "ok", reply
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0",
            str(kernel.workdir / "videos" / "Demo.mp4"),
        ],
        capture_output=True, text=True, check=True,
    )
    assert probe.stdout.strip() == "640,360,15/1"


def test_unembedded_output_links_the_file(kernel):
    reply, messages = kernel.run(
        "jupyter_config.media_embed = False\n"
        "try:\n"
        "    get_ipython().run_line_magic('manim', '-s Demo')\n"
        "finally:\n"
        "    jupyter_config.media_embed = True\n"
    )
    assert reply["status"] == "ok", reply
    images = [h for h in html_outputs(messages) if h.startswith("<img")]
    assert len(images) == 1
    assert 'src="videos/Demo.png?v=' in images[0]


def test_error_inside_construct_is_reported_and_leaves_no_ffmpeg(kernel):
    reply, _ = kernel.run(
        "%%manim -l Broken\n"
        "class Broken(Scene):\n"
        "    def construct(self):\n"
        "        self.play(FadeIn(Dot()), run_time=0.2)\n"
        "        raise ValueError('boom')\n"
    )
    assert reply["status"] == "error"
    assert reply["ename"] == "ValueError"
    reply, messages = kernel.run(
        "import psutil, os\n"
        "me = psutil.Process(os.getpid())\n"
        "print([c.name() for c in me.children(recursive=True)])\n"
    )
    assert reply["status"] == "ok", reply
    assert "ffmpeg" not in stream_text(messages)
