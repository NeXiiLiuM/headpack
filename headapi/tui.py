from __future__ import annotations
import os
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Select, Static
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
        overflow-y: auto;
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

    #preview_area {
        height: 1fr;
    }

    #letter_list {
        width: 1fr;
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

    #head_preview_panel {
        width: 70;
        border-left: solid $primary;
        padding: 0 1;
        align: center top;
    }

    #selected_head_label {
        color: $text-muted;
        text-align: center;
        text-style: italic;
        margin-bottom: 1;
    }

    #face_separator {
        color: $text-muted;
        text-align: center;
        margin-top: 1;
    }

    #face_detail_area {
        height: auto;
    }

    #face_lateral_col {
        width: 33;
    }

    #face_topbot_col {
        width: 33;
    }

    #deploy_btn {
        margin-top: 2;
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("ctrl+d", "deploy",       "Déployer",  priority=True),
        Binding("ctrl+q", "quit",          "Quitter",   priority=True),
        Binding("escape", "quit",          "Quitter",   show=False, priority=True),
        Binding("up",     "preview_up",   "↑ Lettre",  priority=True, show=False),
        Binding("down",   "preview_down", "↓ Lettre",  priority=True, show=False),
        Binding("left",   "rotate_left",  "← Vue",     priority=True, show=False),
        Binding("right",  "rotate_right", "→ Vue",     priority=True, show=False),
        Binding("ctrl+f", "toggle_face",  "^f Face",   priority=True, show=False),
    ]

    _VIEW_LABELS = [
        "↗ avant-droite",
        "↘ droite-arrière",
        "↙ arrière-gauche",
        "↖ gauche-avant",
    ]

    _FLAT_FACE_KEYS   = ["front", "left", "back", "right"]
    _FLAT_FACE_LABELS = ["avant", "gauche", "arrière", "droite"]

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__()
        self._api_key = api_key or os.environ.get("MINECRAFT_HEADS_API_KEY")
        self._heads: list[Head] = []
        self._current_letters: list[ResolvedLetter] = []
        self._loaded = False
        self._fallback: str = "first"
        self._selector: str = "@p"
        self._iso_rotation: int = 0
        self._topbot_idx: int = 0
        self._show_face: bool = False
        self._bg_rgb: tuple[int, int, int] = (18, 18, 18)

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
                yield Label("Fallback", classes="section-label")
                yield Select(
                    [("Premier style dispo", "first"), ("Ignorer la lettre", "skip"), ("Erreur", "error")],
                    id="fallback_select",
                    value="first",
                    allow_blank=False,
                )
                yield Label("Sélecteur cible", classes="section-label")
                yield Input(placeholder="@p", value="@p", id="selector_input")
                yield Label("Clé API", classes="section-label")
                yield Input(placeholder="(optionnelle)", password=True, id="apikey_input")
                yield Button("Déployer", id="deploy_btn", variant="primary")
            with Vertical(id="right_panel"):
                yield Label("Aperçu", classes="panel-title")
                with Horizontal(id="preview_area"):
                    with Vertical(id="letter_list"):
                        yield DataTable(id="preview_table", show_header=False, zebra_stripes=True)
                        yield Label("", id="status_label")
                        yield Label("", id="warning_label")
                    with Vertical(id="head_preview_panel"):
                        yield Label("", id="selected_head_label")
                        yield Static("", id="head_image")
                        yield Label("", id="face_separator")
                        with Horizontal(id="face_detail_area"):
                            with Vertical(id="face_lateral_col"):
                                yield Static("", id="face_lateral_image")
                            with Vertical(id="face_topbot_col"):
                                yield Static("", id="face_topbot_image")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#preview_table", DataTable)
        table.add_columns("Lettre", "", "Tête", "")

        self._populate_worlds()
        self._load_heads()
        self.call_after_refresh(self._update_bg_color)

    def _update_bg_color(self) -> None:
        try:
            c = self.screen.styles.background
            if c.a > 0:
                self._bg_rgb = (c.r, c.g, c.b)
        except Exception:
            pass

    def watch_dark(self, dark: bool) -> None:
        self.call_after_refresh(self._update_bg_color)

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
        elif event.input.id == "selector_input":
            self._selector = event.value or "@p"

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "apikey_input":
            self._api_key = event.value.strip() or None
            self._loaded = False
            self.query_one("#status_label", Label).update("Chargement…")
            self._load_heads()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "style_select":
            self._refresh_preview()
        elif event.select.id == "fallback_select":
            self._fallback = str(event.value)
            self._refresh_preview()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        row_idx = event.cursor_row
        if row_idx < len(self._current_letters):
            self._fetch_and_show_texture(self._current_letters[row_idx].head)

    def action_preview_up(self) -> None:
        self._move_preview_cursor(-1)

    def action_preview_down(self) -> None:
        self._move_preview_cursor(1)

    def _move_preview_cursor(self, delta: int) -> None:
        if not self._current_letters:
            return
        table = self.query_one("#preview_table", DataTable)
        new_row = max(0, min(len(self._current_letters) - 1, table.cursor_row + delta))
        table.move_cursor(row=new_row)
        self._fetch_and_show_texture(self._current_letters[new_row].head)

    def action_rotate_left(self) -> None:
        self._rotate_iso(-1)

    def action_rotate_right(self) -> None:
        self._rotate_iso(1)

    def _rotate_iso(self, delta: int) -> None:
        if not self._current_letters:
            return
        self._iso_rotation = (self._iso_rotation + delta) % 4
        self._topbot_idx = (self._topbot_idx + delta) % 2
        table = self.query_one("#preview_table", DataTable)
        row = table.cursor_row
        if row < len(self._current_letters):
            self._fetch_and_show_texture(self._current_letters[row].head)

    def action_toggle_face(self) -> None:
        self._show_face = not self._show_face
        if not self._show_face:
            self._clear_face_detail()
        table = self.query_one("#preview_table", DataTable)
        row = table.cursor_row
        if self._current_letters and row < len(self._current_letters):
            self._fetch_and_show_texture(self._current_letters[row].head)

    def _clear_face_detail(self) -> None:
        self.query_one("#face_separator",    Label).update("")
        self.query_one("#face_lateral_image", Static).update("")
        self.query_one("#face_topbot_image", Static).update("")

    def _refresh_preview(self) -> None:
        if not self._loaded:
            return

        word = self.query_one("#word_input", Input).value.strip()
        style_val = self.query_one("#style_select", Select).value

        if not word or style_val is Select.BLANK:
            self._clear_preview()
            return

        letters, warnings = resolver.resolve_word(
            word, str(style_val), self._heads, fallback=self._fallback
        )
        self._current_letters = letters
        self._draw_preview(letters, warnings, word)

        if letters:
            self._fetch_and_show_texture(letters[0].head)

    def _clear_preview(self) -> None:
        self.query_one("#preview_table", DataTable).clear()
        self.query_one("#status_label", Label).update("")
        self.query_one("#warning_label", Label).update("")
        self.query_one("#selected_head_label", Label).update("")
        self.query_one("#head_image", Static).update("")
        self._clear_face_detail()
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
        status.update(f"✓  {len(letters)} tête(s) pour « {word.upper()} »" if letters else "")

        warn_label = self.query_one("#warning_label", Label)
        warn_label.update("\n".join(f"⚠ {w}" for w in warnings) if warnings else "")

    @work(thread=True)
    def _fetch_and_show_texture(self, head: Head) -> None:
        from .textures import get_iso_image, get_face_by_name
        from rich_pixels import Pixels

        try:
            iso_pixels = Pixels.from_image(get_iso_image(head, rotation=self._iso_rotation, bg_color=self._bg_rgb))

            lat_px = topbot_px = None
            if self._show_face:
                key = self._FLAT_FACE_KEYS[self._iso_rotation]
                topbot_key = ("top", "bottom")[self._topbot_idx]
                lat_px    = Pixels.from_image(get_face_by_name(head, key,        size=32))
                topbot_px = Pixels.from_image(get_face_by_name(head, topbot_key, size=32))

            self.call_from_thread(
                self._update_head_image, head.name, iso_pixels, lat_px, topbot_px
            )
        except Exception:
            self.call_from_thread(
                self._update_head_image, head.name, "⚠ Aperçu indisponible", None, None
            )

    def _update_head_image(
        self,
        name: str,
        iso_content: object,
        lat_content: object | None,
        topbot_content: object | None,
    ) -> None:
        self.query_one("#selected_head_label", Label).update(
            f"{name}  {self._VIEW_LABELS[self._iso_rotation]}"
        )
        self.query_one("#head_image", Static).update(iso_content)

        if lat_content is not None:
            face_label  = self._FLAT_FACE_LABELS[self._iso_rotation]
            topbot_label = ("dessus", "dessous")[self._topbot_idx]
            self.query_one("#face_separator", Label).update(
                f"─── {face_label} • {topbot_label} ───"
            )
            self.query_one("#face_lateral_image", Static).update(lat_content)
            self.query_one("#face_topbot_image",  Static).update(topbot_content)

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
        content = gen_mcfunction.generate(self._current_letters, self._selector)
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
