from __future__ import annotations
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()

err = Console(stderr=True)


def _get_api_key(cli_key: str | None) -> str | None:
    return cli_key or os.environ.get("MINECRAFT_HEADS_API_KEY")


def _resolve(word: str, style: str, api_key: str | None, no_cache: bool, fallback: str, verbose: bool):
    from . import resolver
    err.print(f"[dim]Chargement des têtes (catégorie alphabet)…[/dim]")
    heads = resolver.load_heads(api_key, no_cache)
    err.print(f"[dim]{len(heads)} têtes chargées.[/dim]")
    letters, warnings = resolver.resolve_word(word, style, heads, fallback)
    for w in warnings:
        err.print(f"[yellow]⚠[/yellow]  {w}")
    if verbose:
        for r in letters:
            suffix = f" [yellow](fallback depuis '{r.head.style()}')[/yellow]" if r.fallback_used else ""
            err.print(f"  [green]{r.char}[/green] → {r.head.name}{suffix}")
    return letters


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("word", required=False)
@click.option("--style", default="quartz", show_default=True, help="Style de tête (quartz, oak, iron…)")
@click.option(
    "--output",
    default="deploy",
    show_default=True,
    type=click.Choice(["deploy", "commands", "mcfunction"], case_sensitive=False),
    help="Mode de sortie.",
)
@click.option("--selector", default="@p", show_default=True, help="Sélecteur Minecraft cible.")
@click.option(
    "--fallback",
    default="first",
    show_default=True,
    type=click.Choice(["first", "skip", "error"], case_sensitive=False),
    help="Comportement si le style est absent pour une lettre.",
)
@click.option("--world-path", default=None, help='Chemin vers le monde Minecraft (mettre entre guillemets si espaces).')
@click.option("--api-key", default=None, help="Clé API minecraft-heads.com.")
@click.option("--install", is_flag=True, help="Installe le datapack dans le monde et quitte.")
@click.option("--clear-cache", is_flag=True, help="Vide le cache local et quitte.")
@click.option("--list-styles", is_flag=True, help="Liste les styles disponibles et quitte.")
@click.option("--list-worlds", is_flag=True, help="Liste les mondes Minecraft disponibles et quitte.")
@click.option("--no-cache", is_flag=True, help="Force la récupération depuis l'API.")
@click.option("-v", "--verbose", is_flag=True, help="Affiche les détails du matching.")
def main(
    word, style, output, selector, fallback, world_path, api_key,
    install, clear_cache, list_styles, list_worlds, no_cache, verbose,
):
    from . import cache as cache_module, resolver, world as world_module
    from .generators import commands as gen_commands, mcfunction as gen_mcfunction

    api_key = _get_api_key(api_key)

    if clear_cache:
        cache_module.invalidate()
        err.print("[green]Cache vidé.[/green]")
        return

    if list_styles:
        heads = resolver.load_heads(api_key, no_cache)
        styles = resolver.list_styles(heads)
        table = Table(title="Styles disponibles", show_header=False)
        table.add_column("Style", style="cyan")
        for s in styles:
            table.add_row(s)
        Console().print(table)
        return

    if list_worlds:
        worlds = world_module.list_worlds()
        if not worlds:
            err.print(f"[red]Aucun monde trouvé dans {world_module.SAVES_DIR}[/red]")
            sys.exit(1)
        table = Table(title="Mondes disponibles", show_header=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("Nom du dossier", style="cyan")
        table.add_column("HeadAPI installé", justify="center")
        table.add_column("Chemin complet", style="dim")
        for i, w in enumerate(worlds):
            installed = "[green]✓[/green]" if world_module.is_installed(w) else "–"
            table.add_row(str(i + 1), w.name, installed, str(w))
        Console().print(table)
        err.print(f'\n[dim]Pour utiliser un monde spécifique :[/dim]')
        err.print(f'  [bold]headapi "MOT" --world-path "{worlds[0]}"[/bold]')
        return

    try:
        wp = world_module.get_world_path(world_path)
    except RuntimeError as e:
        err.print(f"[red]Erreur :[/red] {e}")
        sys.exit(1)

    if install:
        root = world_module.install_skeleton(wp)
        err.print(f"[green]✓[/green] Datapack installé dans : {root}")
        err.print("[dim]En jeu : [bold]/reload[/bold] pour activer.[/dim]")
        return

    if not word:
        from .tui import HeadAPIApp
        HeadAPIApp(api_key=api_key).run()
        return

    try:
        letters = _resolve(word, style, api_key, no_cache, fallback, verbose)
    except ValueError as e:
        err.print(f"[red]Erreur :[/red] {e}")
        sys.exit(1)

    if not letters:
        err.print("[red]Aucune tête résolue. Vérifie le style et le mot.[/red]")
        sys.exit(1)

    if output == "commands":
        content = gen_commands.generate(letters, selector)
        click.echo(content)
        return

    if output == "mcfunction":
        content = gen_mcfunction.generate(letters, selector)
        click.echo(content, nl=False)
        return

    # deploy mode
    if not world_module.is_installed(wp):
        err.print(
            f"[red]Le datapack HeadAPI n'est pas installé dans :[/red] {wp / 'datapacks' / 'headapi'}\n"
            "Lance d'abord : [bold]headapi --install[/bold]"
        )
        sys.exit(1)

    content = gen_mcfunction.generate(letters, selector)
    func_path = world_module.deploy_mcfunction(content, wp)
    err.print(f"[green]✓[/green] {len(letters)} tête(s) prêtes pour [bold]{word.upper()}[/bold] (style : {style})")
    err.print(f"[dim]Fichier : {func_path}[/dim]")
    err.print()
    err.print("En jeu :")
    err.print("  [bold cyan]/reload[/bold cyan]")
    err.print("  [bold cyan]/function headapi:give[/bold cyan]")
