from __future__ import annotations
import os
import sys

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
    from .i18n import t
    err.print(f"[dim]{t('cli_loading_heads')}[/dim]")
    heads = resolver.load_heads(api_key, no_cache)
    err.print(f"[dim]{t('cli_heads_loaded', n=len(heads))}[/dim]")
    letters, warnings = resolver.resolve_word(word, style, heads, fallback)
    for w in warnings:
        err.print(f"[yellow]⚠[/yellow]  {w}")
    if verbose:
        for r in letters:
            suffix = f" [yellow]{t('cli_fallback_used', style=r.head.style())}[/yellow]" if r.fallback_used else ""
            err.print(f"  [green]{r.char}[/green] → {r.head.name}{suffix}")
    return letters


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("word", required=False)
@click.option("--style",      default="quartz", show_default=True)
@click.option("--output",     default="deploy",  show_default=True,
              type=click.Choice(["deploy", "commands", "mcfunction"], case_sensitive=False))
@click.option("--selector",   default="@p",     show_default=True)
@click.option("--fallback",   default="first",  show_default=True,
              type=click.Choice(["first", "skip", "error"], case_sensitive=False))
@click.option("--world-path", default=None)
@click.option("--api-key",    default=None)
@click.option("--lang",       default=None, help="Language: fr or en. Also: HEADPACK_LANG env var.")
@click.option("--install",      is_flag=True)
@click.option("--clear-cache",  is_flag=True)
@click.option("--list-styles",  is_flag=True)
@click.option("--list-worlds",  is_flag=True)
@click.option("--no-cache",     is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
def main(
    word, style, output, selector, fallback, world_path, api_key, lang,
    install, clear_cache, list_styles, list_worlds, no_cache, verbose,
):
    from . import cache as cache_module, resolver, world as world_module
    from .generators import commands as gen_commands, mcfunction as gen_mcfunction
    from .i18n import set_lang, t

    if lang:
        set_lang(lang)

    api_key = _get_api_key(api_key)

    if clear_cache:
        cache_module.invalidate()
        err.print(f"[green]{t('cli_cache_cleared')}[/green]")
        return

    if list_styles:
        heads = resolver.load_heads(api_key, no_cache)
        styles = resolver.list_styles(heads)
        table = Table(title=t("cli_styles_title"), show_header=False)
        table.add_column("Style", style="cyan")
        for s in styles:
            table.add_row(s)
        Console().print(table)
        return

    if list_worlds:
        worlds = world_module.list_worlds()
        if not worlds:
            err.print(f"[red]{t('cli_no_worlds', path=world_module.SAVES_DIR)}[/red]")
            sys.exit(1)
        table = Table(title=t("cli_worlds_title"), show_header=True)
        table.add_column("#", style="dim", width=3)
        table.add_column(t("cli_col_folder"), style="cyan")
        table.add_column(t("cli_col_installed"), justify="center")
        table.add_column(t("cli_col_path"), style="dim")
        for i, w in enumerate(worlds):
            installed = "[green]✓[/green]" if world_module.is_installed(w) else "–"
            table.add_row(str(i + 1), w.name, installed, str(w))
        Console().print(table)
        err.print(f"\n[dim]{t('cli_world_hint')}[/dim]")
        err.print(f"  [bold]{t('cli_world_hint_cmd', path=worlds[0])}[/bold]")
        return

    try:
        wp = world_module.get_world_path(world_path)
    except RuntimeError as e:
        err.print(f"[red]{t('cli_err_world')}[/red] {e}")
        sys.exit(1)

    if install:
        root = world_module.install_skeleton(wp)
        err.print(f"[green]✓[/green] {t('cli_installed_ok', root=root)}")
        err.print(f"[dim]{t('cli_installed_hint')}[/dim]")
        return

    if not word:
        from .tui import HeadPackApp
        HeadPackApp(api_key=api_key).run()
        return

    try:
        letters = _resolve(word, style, api_key, no_cache, fallback, verbose)
    except ValueError as e:
        err.print(f"[red]{t('cli_err_resolve')}[/red] {e}")
        sys.exit(1)

    if not letters:
        err.print(f"[red]{t('cli_no_heads')}[/red]")
        sys.exit(1)

    if output == "commands":
        click.echo(gen_commands.generate(letters, selector))
        return

    if output == "mcfunction":
        click.echo(gen_mcfunction.generate(letters, selector), nl=False)
        return

    # deploy mode
    if not world_module.is_installed(wp):
        err.print(f"[red]{t('cli_not_installed', path=wp / 'datapacks' / 'headpack')}[/red]")
        sys.exit(1)

    func_path = world_module.deploy_mcfunction(gen_mcfunction.generate(letters, selector), wp)
    err.print(f"[green]✓[/green] {t('cli_deploy_ok', n=len(letters), word=word.upper(), style=style)}")
    err.print(f"[dim]{t('cli_deploy_file', path=func_path)}[/dim]")
    err.print()
    err.print(t("cli_deploy_ingame"))
    err.print("  [bold cyan]/reload[/bold cyan]")
    err.print("  [bold cyan]/function headpack:give[/bold cyan]")
