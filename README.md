# HeadPack

A CLI/TUI tool to spell words using Minecraft player heads — fetches alphabet head skins from [minecraft-heads.com](https://minecraft-heads.com), generates the `/give` commands, and deploys them as a datapack directly into your world.

```
headpack MINECRAFT
```

![HeadPack TUI](example.png)

---

## Features

- **Interactive TUI** with a real-time isometric 3D preview of each head
- **4 rotation views** (←/→) with synchronized flat face inspection (Ctrl+F)
- **Multiple styles** — quartz, oak, iron, birch, and many more
- **Flexible fallback** — use the closest available style, skip missing letters, or raise an error
- **One-command deploy** — installs a datapack and writes the mcfunction to your world
- **CLI mode** — pipe-friendly output for scripting (`--output commands` or `--output mcfunction`)

---

## Requirements

- Python 3.11+
- Minecraft Java Edition (for deployment)
- A terminal with true-color support for the TUI preview

---

## Installation

```bash
pip install headpack
```

Or from source:

```bash
git clone https://github.com/NeXiiLiuM/headpack
cd headpack
pip install -e .
```

---

## Usage

### TUI (interactive)

```bash
headpack        # launch the TUI
hpk             # short alias
```

Type your word, pick a style, select your world, and press **Ctrl+D** to deploy.

#### TUI keyboard shortcuts

| Key | Action |
|---|---|
| ↑ / ↓ | Navigate letters |
| ← / → | Rotate head preview (4 views) |
| Ctrl+F | Toggle flat face view (lateral + top/bottom) |
| Ctrl+D | Deploy to selected world |
| Ctrl+Q / Esc | Quit |

### CLI

```bash
# Deploy directly (default)
headpack "HELLO" --style quartz

# Print /give commands to stdout
headpack "HELLO" --style oak --output commands

# Generate a .mcfunction file
headpack "HELLO" --output mcfunction > give.mcfunction
```

#### Options

| Option | Default | Description |
|---|---|---|
| `--style` | `quartz` | Head style (quartz, oak, iron, birch…) |
| `--fallback` | `first` | `first` = use closest style · `skip` = omit letter · `error` = fail |
| `--selector` | `@p` | Minecraft target selector (`@p`, `@a`, player name…) |
| `--output` | `deploy` | `deploy` · `commands` · `mcfunction` |
| `--world-path` | auto-detect | Path to Minecraft world folder |
| `--api-key` | env var | minecraft-heads.com API key |
| `--install` | — | Install the datapack into the world and exit |
| `--list-styles` | — | List all available head styles |
| `--list-worlds` | — | List detected Minecraft worlds |
| `--no-cache` | — | Force a fresh fetch from the API |

---

## Deployment

HeadPack installs a lightweight datapack into your world and writes a `give.mcfunction` file. After deploying:

```
/reload
/function headpack:give
```

The first time, run `headpack --install` (or use the deploy button in the TUI — it installs automatically).

---

## Configuration

| Variable | Description |
|---|---|
| `MINECRAFT_HEADS_API_KEY` | API key for minecraft-heads.com (optional, increases rate limits) |
| `HEADPACK_WORLD_PATH` | Default world path (overrides auto-detection) |

A `.env` file in the working directory is loaded automatically.

---

## Cache

Head data is cached locally at `~/.cache/headpack/` with a 7-day TTL. Clear it with:

```bash
headpack --clear-cache
```

---

## License

No license, do what you want (i am not responsible for anything you do with this tool)
