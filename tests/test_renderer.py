from __future__ import annotations

from io import StringIO

from prompt_toolkit.application import Application
from prompt_toolkit.data_structures import Size
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.output.vt100 import Vt100_Output

WIDTH = 40
PADDING = " " * 20


class _Toolbar:
    """One styled row, rendered through the real `Renderer` into a string."""

    def __init__(self, style: str) -> None:
        self.style = style
        self.stdout = StringIO()
        self.output = Vt100_Output(
            self.stdout, lambda: Size(rows=5, columns=WIDTH), term="xterm"
        )
        self.window = Window(
            FormattedTextControl("tb"), height=1, style=lambda: self.style
        )

    def render(self, app: Application[None]) -> str:
        start = len(self.stdout.getvalue())
        app.renderer.render(app, app.layout)
        return self.stdout.getvalue()[start:]


def _run(style: str, *restyles: str) -> list[str]:
    toolbar = _Toolbar(style)
    with create_pipe_input() as inp:
        app = Application(
            layout=Layout(toolbar.window), input=inp, output=toolbar.output
        )
        outputs = [toolbar.render(app)]
        for restyle in restyles:
            toolbar.style = restyle
            outputs.append(toolbar.render(app))
    return outputs


def test_background_fill_uses_erase_end_of_line():
    # Literal spaces up to the right edge would be rewrapped by terminals that
    # become narrower, leaving copies of the prompt behind (#1933).
    (out,) = _run("bg:ansiblue")
    assert "tb\x1b[K" in out
    assert PADDING not in out


def test_reverse_fill_with_known_foreground_uses_erase_end_of_line():
    (out,) = _run("reverse ansiwhite bg:ansiblack")
    assert "\x1b[K" in out
    assert PADDING not in out
    # The text keeps reverse video; the fill gets fg/bg swapped instead.
    assert "\x1b[0;97;40;7mtb" in out
    assert "\x1b[0;30;107m\x1b[K" in out


def test_reverse_fill_with_default_colors_keeps_spaces():
    (out,) = _run("reverse")
    assert PADDING in out


def test_unchanged_fill_is_not_repainted():
    first, second = _run("bg:ansiblue", "bg:ansiblue")
    assert "\x1b[K" in first
    assert "\x1b[K" not in second


def test_removed_fill_is_erased():
    _, second = _run("bg:ansiblue", "")
    assert "\x1b[0m\x1b[K" in second


def test_invisible_blanks_are_not_written():
    # A written space marks a row as used; when the terminal gets shorter it
    # then drops rows from the top, leaving copies of the prompt (#1933).
    toolbar = _Toolbar("class:no-visual-style")
    toolbar.window.height = 3
    with create_pipe_input() as inp:
        app = Application(
            layout=Layout(toolbar.window), input=inp, output=toolbar.output
        )
        out = toolbar.render(app)
    assert "tb" in out
    assert " " not in out
