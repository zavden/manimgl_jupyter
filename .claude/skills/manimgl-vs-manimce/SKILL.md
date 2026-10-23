---
name: manimgl-vs-manimce
description: ManimGL (3b1b's manimlib) API essentials and how it differs from ManimCE (the `manim` community package). Use when writing or fixing a scene for manimlib or manimgl_jupyter, when code mixes ManimCE names (Create, MathTex, MovingCameraScene, self.camera.frame, config.frame_width, set_camera_orientation, add_fixed_in_frame_mobjects, GRAY_A) into a manimlib project, or when unsure which name ManimGL uses for something.
---

# ManimGL is not ManimCE

Same ancestry, different packages. ManimGL is `manimlib` (`from manimlib import *`,
command `manimgl`); ManimCE is `manim` (`from manim import *`, command `manim`).
Code written for one does not run on the other. In a notebook with
manimgl_jupyter the names come from `from manimgl_jupyter import *`.

## Name map, ManimCE to ManimGL

| ManimCE | ManimGL |
|---|---|
| `Create(m)` | `ShowCreation(m)` |
| `MathTex(r"x^2")` | `Tex(R"x^2")`, math mode by default |
| `Tex("words")`, text mode | `TexText("words")` |
| `Text`, `MarkupText`, `Code` | same names |
| `Unwrite` | none; `FadeOut` or `Uncreate` |
| `Circumscribe(m)` | none; `FlashAround(m)` or `Indicate(m)` |
| `Wiggle(m)` | `WiggleOutThenIn(m)` |
| `MovingCameraScene`, `self.camera.frame` | any `Scene`; the camera is `self.frame`, a `CameraFrame` |
| `ThreeDScene.set_camera_orientation(phi=, theta=)` | `self.frame.reorient(theta_deg, phi_deg, gamma_deg=0, center=None, height=None)`. `ThreeDScene` exists in GL too: depth test on, 4 samples, default orientation `(-30, 70)` |
| `self.move_camera(phi=, theta=)` | `self.play(self.frame.animate.reorient(theta, phi))` |
| `self.begin_ambient_camera_rotation(rate)` | `self.frame.add_updater(lambda f, dt: f.increment_theta(dt * rate))` |
| `self.add_fixed_in_frame_mobjects(m)` | `m.fix_in_frame()` then `self.add(m)` |
| `config.frame_width`, `config.frame_height` | constants `FRAME_WIDTH`, `FRAME_HEIGHT`, `FRAME_X_RADIUS`, `FRAME_Y_RADIUS` |
| `config.background_color = X` | `-c X` on the command line, or `camera: background_color` in `custom_config.yml` |
| `axes.plot(f, x_range=, color=)` | `axes.get_graph(f, x_range=, color=)` |
| `axes.input_to_graph_point(x, graph)` | `axes.i2gp(x, graph)` |
| `axes.get_area(graph, x_range)` | `axes.get_area_under_graph(graph, x_range, fill_color, fill_opacity)` |
| `axes.get_vertical_line(point)` | `axes.get_v_line(point)`, `axes.get_v_line_to_graph(x, graph)`, `get_h_line`, `get_h_line_to_graph` |
| `axes.get_riemann_rectangles(graph, x_range, dx)` | same |
| `Surface(func, u_range, v_range)` | `ParametricSurface(func, u_range, v_range)`; `Surface` in GL is the base class |
| `Dot3D` | `Sphere(radius=0.1)`, or `TrueDot` / `GlowDot` (point-cloud dots, cheap in quantity) |
| `Line3D` | `Line`; every mobject lives in 3D |
| `always_redraw(f)` | same; plus `always(m.method, *args)` and `f_always(m.method, lambda: ...)` |
| `m.animate.method()` | same; `m.animate(run_time=2, rate_func=linear).method()` also works |
| `TransformMatchingTex`, `TransformMatchingShapes` | same; `TransformMatchingStrings` for `Text` and `Tex` alike |
| `GRAY_A`..`GRAY_E`, `GREY_*` | only `GREY_A`..`GREY_E`; the `GRAY_*` names do not exist |
| `ManimColor` | plain hex strings or `colour.Color`; constants `BLUE_E`..`BLUE_A`, `BLUE`, `TEAL`, `GREEN`, `YELLOW`, `GOLD`, `RED`, `MAROON`, `PURPLE`, `GREY`, `PINK`, `ORANGE`, `WHITE`, `BLACK` |
| `TracedPath` | same; also `TracingTail` |
| `ArrowVectorField`, `StreamLines` | `VectorField`, `StreamLines` |
| `config.pixel_width`, `self.renderer` | nothing exposed; resolution comes from the flags (`-l`, `-m`, `--hd`, `-r WxH`) |
| `manim file.py Scene -pql` | `manimgl file.py Scene` opens a window; `-w` writes, `-l` low quality, `-s` last frame, `-o` opens the file |
| `%%manim -qm Scene` | `%%manim -m Scene` with manimgl_jupyter |

## Same in both

`VGroup`, `Group`, `.next_to`, `.to_edge`, `.shift`, `.scale`, `.move_to`, `.arrange`,
`.set_color`, `.set_fill(color, opacity)`, `.set_stroke(color, width)`,
`self.add` / `remove` / `play` / `wait`, `run_time=`, `lag_ratio=`,
`rate_func=smooth | linear | there_and_back | rush_into | rush_from`,
`LaggedStart`, `AnimationGroup`, `Succession`, `ValueTracker`, `DecimalNumber`,
`Integer`, `NumberLine`, `NumberPlane`, `Axes`, `ThreeDAxes`, `Brace`,
`SurroundingRectangle`, `Arrow`, `Vector`, `Dot`, `Line`, `Circle`, `Square`,
`Polygon`, `Sphere`, `Cube`, `Prism`, `ImageMobject`, `SVGMobject`, `Rotate`,
`Rotating`, `Indicate`, `Flash`, `Write`, `DrawBorderThenFill`, `FadeIn`,
`FadeOut`, `GrowFromCenter`, `Transform`, `ReplacementTransform`,
`FadeTransform`, `m.add_updater(lambda m, dt: ...)`, `m.clear_updaters()`.

## ManimGL specifics worth using

- `Tex(R"a + b", isolate=["a", "b"], t2c={"a": BLUE})`; `tex["a"]` selects that part.
  `Text("hola", font="Consolas", font_size=48, t2c={"hola": YELLOW})`.
- `m.fix_in_frame()` pins 2D elements while the frame moves through 3D.
- `m.set_backstroke(BLACK, 5)` outlines text over busy backgrounds;
  `m.set_shading(reflectiveness, gloss, shadow)` lights 3D surfaces.
- `self.frame.set_height(h)`, `self.frame.move_to(p)`, `self.frame.reorient(...)`
  zoom, pan and rotate; animate them with `self.frame.animate`, or give the frame
  an updater for continuous motion.
- `always(label.next_to, dot, UP)` keeps a relation; `f_always(num.set_value,
  tracker.get_value)` feeds a method from callables every frame.
- `custom_config.yml` in the working directory sets output directories,
  resolution, fonts, colors and the TeX template.
- Interactive development is command-line only: `self.embed()` inside
  `construct` drops into IPython with the window live, and `InteractiveScene`
  adds selection and dragging. Both do nothing without a window, so nothing in a
  notebook.

## Skeleton

```python
from manimlib import *


class Example(Scene):
    def construct(self):
        axes = Axes(x_range=(-3, 3), y_range=(-1, 4), width=10, height=6)
        axes.add_coordinate_labels()
        graph = axes.get_graph(lambda x: x**2 / 2, color=BLUE)
        label = Tex(R"y = \frac{x^2}{2}", t2c={"x": BLUE})
        label.next_to(graph.get_end(), LEFT)
        self.play(Write(axes), ShowCreation(graph), FadeIn(label))

        x = ValueTracker(-2)
        dot = GlowDot(color=YELLOW)
        f_always(dot.move_to, lambda: axes.i2gp(x.get_value(), graph))
        self.add(dot)
        self.play(x.animate.set_value(2), run_time=3)

        self.play(self.frame.animate.reorient(20, 60).set_height(10), run_time=2)
        self.wait()
```

```bash
manimgl example.py Example        # window, interactive
manimgl example.py Example -w     # videos/Example.mp4
manimgl example.py Example -s -o  # last frame as PNG, opened
```
