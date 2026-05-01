# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Part of `personal-os`

This repo is a satellite of [`personal-os`](file:///Users/jmattiello/Workspace/personal-os) at `~/Workspace/personal-os`. A fresh agent session here should read `personal-os/AGENTS.md` first for shared conventions:

- **`VOICE.md`** — voice rules for any public-facing prose (README, contribution-guide copy).
- **`decisions/`** — cross-repo MADR-numbered ADRs.
- **`journal/`** — daily orchestration log.
- **`INBOX.md`** — things-to-act-on across all projects.
- **`wiki/projects-index.md`** — registry of every active repo.

Don't edit `personal-os/raw/` from a satellite — that's the central drop-zone, one-way.

## Project Overview

**provenance-data** — test ROMs (legal homebrew / open-source / public domain only), screenshots, cover artwork, and the Python scripts that index them for Provenance's metadata pipeline.

## Repo layout

- `ROMs/` — homebrew + open-domain ROMs, named per system (e.g. `My Demo Rom.gen` for Genesis). Zipped flat.
- `Databases/` — game DB files (sqlite + JSON).
- `analyze_json.py`, `convert_to_sqlite.py`, `scan_roms.py`, `rom_downloader.py` — index-generation and maintenance scripts.
- `assets.cores.json`, `artwork_cache.json` — generated index artifacts.
- `games.db` — sqlite snapshot.
- `index.html` + `CNAME` — GitHub Pages frontend.
- `retroarch.cfg` — RetroArch config bundled for testing.

## Hard rules

- **Legal ROMs only.** Homebrew, open-source, or public-domain. **Never** commit a ROM that isn't clearly free-to-distribute. If unsure, don't add it.
- **Naming convention is load-bearing.** ROMs follow `<Title> (<Region/Tags>).<system-extension>` and ship in flat zips with the same base name. The scanner depends on the format — don't rename ad-hoc.
- **Artwork pairing**: `<ROMNAME>-screenshot.png` and `<ROMNAME>-cover.png` (or `.jpg`/`.jpeg`). Run `python scan_roms.py` after adding artwork to regenerate the index.

## Generated files

- Anything under `Databases/` produced by `convert_to_sqlite.py` is regenerated. Don't hand-edit; edit the JSON sources or the script.
- `artwork_cache.json` is generated from the artwork present in this repo + remote sources.

## Workflow

1. Add legal ROM → flat zip → correct directory.
2. Add artwork in the `<ROMNAME>-screenshot|cover.<ext>` pattern.
3. Run `python scan_roms.py` to refresh the index.
4. Commit + PR.
