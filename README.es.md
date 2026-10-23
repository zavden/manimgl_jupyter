# manimgl_jupyter

ManimGL dentro de notebooks de Jupyter, VSCode incluido, con una celda mágica `%%manim` al estilo de ManimCE.

```python
from manimgl_jupyter import *
```

```python
%%manim -l HolaManimGL
class HolaManimGL(Scene):
    def construct(self):
        self.play(Write(Text("ManimGL en un notebook")))
```

La celda renderiza la escena a un archivo, sin abrir ventana, y muestra el video justo debajo.

*In English: [README.md](README.md)*

## Por qué existe

Dos cosas dejan a ManimGL fuera de los notebooks:

1. `manimlib` parsea `sys.argv` en el momento en que se importa. Un kernel de Jupyter arranca con argumentos que el parser de manimgl no conoce, y VSCode en particular le pasa `--f=<archivo de conexión>`, que argparse rechaza por ambiguo (`--fps`, `--finder`, `--file_name`, `--full_screen`). `from manimlib import *` muere con `SystemExit: 2` antes de poder hacer nada.
2. `manimgl` renderiza a una ventana o a un archivo desde la línea de comandos. Nada muestra un resultado dentro de un notebook.

`manimgl_jupyter` resuelve ambas cosas sin cambiar una línea de manimlib. Es un solo módulo.

## Requisitos

- Python 3.10 o más reciente.
- Un **ManimGL reciente desde GitHub**, instalado y funcionando desde la línea de comandos (`manimgl example_scenes.py OpeningManimExample -w`). El módulo usa la configuración de manimlib basada en `manim_config`, anterior a la cual es la versión de PyPI `manimgl 1.7.2`, así que instala manimgl desde su repositorio (o tu fork) primero.
- Lo que manimgl ya necesita: `ffmpeg` en el PATH, LaTeX para `Tex`, y un driver de GPU que wgpu pueda usar (Vulkan, Metal o DirectX 12).

## Instalación

En el mismo entorno que tiene manimgl:

```bash
pip install git+https://github.com/TU-USUARIO/manimgl_jupyter.git
```

o clona el repositorio y ejecuta `pip install -e .` dentro. La instalación trae también `ipykernel` e `ipywidgets`, para que el entorno sirva como kernel de notebook y la barra de progreso se vea como widget.

En VSCode, abre un `.ipynb` y elige como kernel el intérprete de ese entorno. Para ver el kernel desde notebooks en cualquier carpeta, regístralo una vez:

```bash
python -m ipykernel install --user --name manimgl
```

## Uso

### Celda mágica

```python
%%manim -l NombreEscena
class NombreEscena(Scene):
    def construct(self):
        ...
```

El cuerpo de la celda es Python normal y se ejecuta primero en el espacio de nombres del notebook, así que las funciones auxiliares y constantes definidas ahí quedan disponibles para celdas posteriores. Después se renderiza y muestra la escena indicada. `%%manimgl` es un alias de `%%manim`.

### Magia de línea

```python
%manim -s NombreEscena
```

renderiza una escena definida en una celda anterior.

### Qué escenas

- Con nombres en la línea, esas escenas.
- Sin nombre, todas las subclases de `Scene` que define la celda, en orden.
- Con `-a`, todas las escenas definidas en el notebook hasta ese momento.

### Flags

Son los flags del comando `manimgl`, parseados por el propio manimgl. Los habituales:

| Flag | Efecto |
|---|---|
| `-l` `-m` `--hd` `--uhd` | 854x480, 1280x720, 1920x1080, 3840x2160 |
| `-r 1280x720` | cualquier resolución |
| `--fps 60` | fotogramas por segundo |
| `-s` | omite las animaciones y guarda el último fotograma como PNG |
| `-i` | escribe un GIF |
| `-t` | fondo transparente, `.mov` con ProRes (ver Notas) |
| `-c "#112233"` | color de fondo |
| `-n 3` o `-n 3,6` | empieza en la animación 3, o renderiza de la 3 a la 6 |
| `-a` | renderiza todas las escenas |
| `--prerun` | hace primero una pasada en seco para que la barra de progreso tenga total |
| `--file_name NOMBRE`, `--video_dir DIR` | nombre y carpeta de salida |
| `-q` | sin barra de progreso ni línea de "File ready" |

`%manim -h` muestra la lista completa. Renderizar en un notebook siempre escribe a archivo; no se abre ventana, y lo que depende de ella (`self.embed()`, `-p`, el modo interactivo) no hace nada.

### Salida

Los archivos van a donde los pondría `manimgl -w`: `videos/` junto al notebook (el directorio de trabajo del kernel), o donde diga el `custom_config.yml` de ese directorio. El resultado se incrusta en base64 en la salida de la celda.

```python
jupyter_config.media_width = "100%"    # max-width CSS de lo mostrado, por defecto "60%"
jupyter_config.media_embed = False     # enlazar el archivo en vez de incrustarlo
jupyter_config.video_attributes = "controls loop"   # por defecto "controls autoplay loop"
```

Incrustar es lo que VSCode necesita, porque su visor de notebooks no puede cargar archivos locales. Enlazar mantiene pequeño el `.ipynb` y va bien en JupyterLab.

### Desde Python

```python
path = render_scene(NombreEscena, "-l --fps 24")   # el Path escrito, sin mostrar nada
show_media(path)
```

### Como extensión de IPython

`%load_ext manimgl_jupyter` también registra la magia. Igualmente debe ejecutarse antes de cualquier importación de `manimlib`, por la razón explicada arriba.

## Cómo funciona

1. **La importación.** El módulo guarda `sys.argv`, lo deja en `["manimgl"]`, importa `manimlib` (reexportando todos sus nombres) y lo restaura. manimlib construye su configuración global como si se ejecutara sin argumentos.
2. **La celda.** `%%manim` ejecuta el cuerpo de la celda a través de IPython, de modo que las clases quedan en el espacio de nombres del notebook y los errores se muestran como siempre. Si el cuerpo falla, no se renderiza nada.
3. **Los flags.** La línea se entrega al propio parser de manimlib llamando a `manimlib.config.initialize_manim_config()` con `sys.argv` puesto a `manimgl -w <flags>`. El resultado es exactamente la configuración que usaría la línea de comandos, con `-w` convirtiéndolo en un render a archivo sin ventana. El primer argumento posicional, que el parser toma por un archivo, aquí es un nombre de escena.
4. **El render.** La clase de la escena se instancia con esa configuración (`camera_config` y `file_writer_config` se pasan explícitamente, así que la configuración global no se toca) y se llama a `scene.run()`. Sin ventana, la `Camera` de manimlib crea su propio dispositivo wgpu fuera de pantalla, y `SceneFileWriter` envía los fotogramas a ffmpeg por una tubería. Con `--prerun`, una pasada previa sin animaciones cuenta los fotogramas para la barra de progreso.
5. **La visualización.** El mp4, PNG o GIF resultante se lee y se incrusta como data URI en base64 dentro de un elemento `<video>` o `<img>`. Con `media_embed = False` se enlaza en ruta relativa al notebook, con la fecha de modificación del archivo para evitar la caché.
6. **Los errores.** Si la escena lanza una excepción, se cierra la tubería de ffmpeg para no dejar un proceso esperando, y la excepción llega a la celda.

## Estructura

```
manimgl_jupyter/
├── manimgl_jupyter.py        el módulo: guarda de argv, constructor de config, render, visualización, magia
├── pyproject.toml            empaquetado; instala el módulo como un único archivo de nivel superior
├── examples/demo.ipynb       un notebook para probarlo
├── tests/test_notebook.py    tests de punta a punta a través de un kernel real lanzado como lo hace VSCode
├── .claude/skills/           skills de Claude Code, ver abajo
├── README.md, README.es.md
└── LICENSE
```

Dentro del módulo, de arriba abajo: la guarda de argv y las importaciones; `jupyter_config`; `split_flags` y `build_config`; el descubrimiento de escenas (`_scene_classes_in`); `render_scene` / `_render`; `show_media`; la clase `ManimglMagics`; y el registro (`load_ipython_extension` y registro automático al importar).

## Notas y límites

- `-t` escribe un `.mov` con ProRes, que los navegadores no reproducen; en su lugar se registra la ruta.
- Los GIF ocupan mucho incrustados. Mejor mp4 salvo que necesites un GIF.
- Los medios incrustados hacen crecer el `.ipynb`. Limpia las salidas antes de subir notebooks, o usa `media_embed = False` donde los archivos enlazados se muestren.
- Cada render crea su propio dispositivo de GPU y vuelve a compilar los shaders; es una fracción de segundo. LaTeX y texto los cachea manimlib en disco.
- Si una escena falla a medias queda un `NombreEscena_temp.mp4`, igual que en la línea de comandos. Interrumpir el kernel conserva y muestra el video parcial.
- Probado en Linux. Nada en el módulo depende de la plataforma; en Windows se conservan las barras invertidas de las rutas pasadas como flags.

## Skills de Claude Code

`.claude/skills/` contiene tres skills en el formato [Agent Skills](https://agentskills.io), que Claude Code carga automáticamente al trabajar en este repositorio. Copia una carpeta a `~/.claude/skills/` para usarla en cualquier sitio.

| Skill | Para |
|---|---|
| `manimgl-notebook` | renderizar escenas en notebooks: flags, salida, ajustes de visualización, resolución de problemas |
| `manimgl-vs-manimce` | la API de ManimGL y sus diferencias con ManimCE, para escribir escenas con los nombres correctos |
| `manimgl-jupyter-dev` | cómo funciona el módulo por dentro, de qué depende en manimlib y cómo probarlo |

## Desarrollo

```bash
pip install -e .[test]
pytest
```

Los tests arrancan un ipykernel real con `--f=<archivo de conexión>`, la forma de lanzamiento que usa VSCode, y ejecutan celdas a través de él con la raíz del repositorio en `PYTHONPATH`. Necesitan GPU y ffmpeg, como manimgl, y tardan alrededor de un minuto.

## Licencia

MIT.
