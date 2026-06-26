from __future__ import annotations
import os
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Select
from textual import work

from . import resolver, world as world_module
from .generators import mcfunction as gen_mcfunction
from .models import Head, ResolvedLetter


class HeadAPIApp(App):
    TITLE = "HeadAPI"
    SUB_TITLE = "Générateur de têtes Minecraft alphabétiques"

    CSS = """
    #main {
        height: 1fr;
    }

    #left_panel {
        width: 34;
        border: solid $primary;
        padding: 1 2;
    }

    #left_panel .section-label {
        margin-top: 1;
        color: $text-muted;
    }

    #right_panel {
        width: 1fr;
        border: solid $primary;
        padding: 1 2;
    }

    .panel-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #preview_table {
        height: 1fr;
    }

    #status_label {
        margin-top: 1;
        color: $success;
    }

    #warning_label {
        color: $warning;
    }

    #deploy_btn {
        margin-top: 2;
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("ctrl+d", "deploy", "Déployer", priority=True),
        Binding("ctrl+q", "quit", "Quitter", priority=True),
        Binding("escape", "quit", "Quitter", show=False, priority=True),
    ]

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__()
        self._api_key = api_key or os.environ.get("MINECRAFT_HEADS_API_KEY")
        self._heads: list[Head] = []
        self._current_letters: list[ResolvedLetter] = []
        self._loaded = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            with Vertical(id="left_panel"):
                yield Label("Configuration", classes="panel-title")
                yield Label("Mot à épeler", classes="section-label")
                yield Input(placeholder="ex: MINECRAFT", id="word_input")
                yield Label("Style", classes="section-label")
                yield Select([], id="style_select", prompt="Chargement…")
                yield Label("Monde", classes="section-label")
                yield Select([], id="world_select", prompt="Aucun monde")
                yield Button("Déployer", id="deploy_btn", variant="primary")
            with Vertical(id="right_panel"):
                yield Label("Aperçu", classes="panel-title")
                yield DataTable(id="preview_table", show_header=False, zebra_stripes=True)
                yield Label("", id="status_label")
                yield Label("", id="warning_label")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#preview_table", DataTable)
        table.add_columns("Lettre", "", "Tête", "")

        self._populate_worlds()
        self._load_heads()

    def _populate_worlds(self) -> None:
        worlds = world_module.list_worlds()
        select = self.query_one("#world_select", Select)
        if worlds:
            select.set_options([(w.name, str(w)) for w in worlds])
            select.value = str(worlds[0])

    @work(thread=True)
    def _load_heads(self) -> None:
        heads = resolver.load_heads(self._api_key, no_cache=False)
        styles = resolver.list_styles(heads)
        self.call_from_thread(self._on_heads_loaded, heads, styles)

    def _on_heads_loaded(self, heads: list[Head], styles: list[str]) -> None:
        self._heads = heads
        self._loaded = True

        style_select = self.query_one("#style_select", Select)
        style_select.set_options([(s, s) for s in styles])
        try:
            style_select.value = "quartz"
        except Exception:
            pass

        self._refresh_preview()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "word_input":
            self._refresh_preview()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "style_select":
            self._refresh_preview()

    def _refresh_preview(self) -> None:
        if not self._loaded:
            return

        word = self.query_one("#word_input", Input).value.strip()
        style_val = self.query_one("#style_select", Select).value

        if not word or style_val is Select.BLANK:
            self._clear_preview()
            return

        letters, warnings = resolver.resolve_word(
            word, str(style_val), self._heads, fallback="first"
        )
        self._current_letters = letters
        self._draw_preview(letters, warnings, word)

    def _clear_preview(self) -> None:
        self.query_one("#preview_table", DataTable).clear()
        self.query_one("#status_label", Label).update("")
        self.query_one("#warning_label", Label).update("")
        self._current_letters = []

    def _draw_preview(
        self,
        letters: list[ResolvedLetter],
        warnings: list[str],
        word: str,
    ) -> None:
        table = self.query_one("#preview_table", DataTable)
        table.clear()

        for r in letters:
            marker = "⚠" if r.fallback_used else "✓"
            style_note = f"  (↳ {r.head.style()})" if r.fallback_used else ""
            table.add_row(r.char, "→", r.head.name + style_note, marker)

        status = self.query_one("#status_label", Label)
        if letters:
            status.update(f"✓  {len(letters)} tête(s) pour « {word.upper()} »")
        else:
            status.update("")

        warn_label = self.query_one("#warning_label", Label)
        warn_label.update("\n".join(f"⚠ {w}" for w in warnings) if warnings else "")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "deploy_btn":
            self.action_deploy()

    def action_deploy(self) -> None:
        if not self._current_letters:
            self.query_one("#status_label", Label).update("⚠ Tape un mot d'abord.")
            return
        world_val = self.query_one("#world_select", Select).value
        if world_val is Select.BLANK:
            self.query_one("#status_label", Label).update("⚠ Sélectionne un monde d'abord.")
            return
        self._deploy(Path(str(world_val)))

    @work(thread=True)
    def _deploy(self, wp: Path) -> None:
        if not world_module.is_installed(wp):
            world_module.install_skeleton(wp)
        content = gen_mcfunction.generate(self._current_letters, "@p")
        world_module.deploy_mcfunction(content, wp)
        self.call_from_thread(self._on_deploy_done)

    def _on_deploy_done(self) -> None:
        self.notify(
            "En jeu : /reload  puis  /function headapi:give",
            title="✓ Déployé avec succès !",
            timeout=6,
        )
        btn = self.query_one("#deploy_btn", Button)
        btn.variant = "success"
        self.set_timer(3.0, self._reset_deploy_btn)

    def _reset_deploy_btn(self) -> None:
        self.query_one("#deploy_btn", Button).variant = "primary"
