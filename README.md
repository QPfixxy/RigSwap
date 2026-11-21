<div align="center">

<img src="docs/logo/rigswap-icon.svg" width="112" alt="RigSwap logo">

# RigSwap

**One-click graphics settings for every way you play.**

Keep a separate copy of each game's graphics settings for each hardware setup, such as a handheld, an eGPU dock or a laptop on battery, and switch all of them at once, by hand or automatically when you dock.

[![CI](https://github.com/QPfixxy/RigSwap/actions/workflows/ci.yml/badge.svg)](https://github.com/QPfixxy/RigSwap/actions/workflows/ci.yml)
![Platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20Linux-informational)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-green)](LICENSE)
![Status](https://img.shields.io/badge/status-pre--release-orange)

</div>

![RigSwap main window](docs/images/main-window.png)

## Why

Handheld gaming PCs and laptops are often plugged into an external GPU. Docked, you want 4K at ultra settings. On the go, you want 720p at low settings and a long battery life. Games keep only one set of graphics settings, so every change of setup means opening each game's options menu again.

RigSwap saves each game's settings once for each setup. Pick a setup, or just plug in your dock, and every game's settings are swapped in one step.

## Features

### Switching

- **Setups, not per-game profiles.** Define setups such as `Handheld`, `eGPU Dock` and `Laptop on Battery` once. Each game keeps one saved config per setup, and switching applies all of them together.
- **Switches by itself.** Tell a setup when to apply, for example "an external GPU is connected" or "on battery", and RigSwap switches when you dock or undock. It recognises an eGPU from how Windows or Linux reports the device, so any brand or dock works (Thunderbolt, USB4, OCuLink). It runs in the tray and can start at login, or as a background service on Linux.
- **Keeps your tweaks.** When you switch away from a setup, the settings you're using are saved back into it. Lock a setup to keep a known-good config exactly as it is.

### Finding games and their settings

- **Imports from your launchers.** Steam, Epic Games and GOG on Windows, plus Windows' own list of recognised games; Steam, Heroic (GOG, Epic, Amazon) and Lutris on Linux, including Flatpak installs and the Proton or Wine prefixes games run in.
- **Finds config files for you.** RigSwap recognises Unreal Engine, Unity and Source games by itself, and can also look games up in a free, community-maintained database of where more than 12,000 games keep their settings (the [Ludusavi manifest](https://github.com/mtkennerly/ludusavi-manifest), built from [PCGamingWiki](https://www.pcgamingwiki.com/)).
- **Files, folders and registry keys.** A game's config can be a file, several files, a whole folder or a registry key, the way many Unity games store their settings, on Windows and inside Proton or Wine prefixes.
- **Learns where unknown games keep their settings.** For a game nothing else recognises, **Learn…** watches what changes while you change one setting in the game, and offers exactly those files or registry values.
- **Works with any game.** Anything can also be added by hand.

### Safety

- **Never switches under a running game.** If you unplug mid-game, RigSwap waits until you close the game, and tells you so.
- **Backs up before every switch** and writes atomically, so an interrupted switch can't leave a half-written config. If anything fails partway through, everything is rolled back, and **Undo** puts back the configs from before the last switch.
- **Protects your saves.** Some games keep saves next to their settings. Include and exclude patterns keep saves out, folders and keys that mix the two are only ever suggested, and switching never deletes files.
- **Spots outside changes.** RigSwap shows when a game's settings changed since they were saved (a game update or cloud sync can do that) and can put the saved copy back.

<p align="center">
  <img src="docs/images/folder-files.png" width="480" alt="Choosing which files in a config folder belong to the snapshot">
  <br><sub>Choosing which files in a config folder are swapped, so saves stay untouched</sub>
</p>

## Platform support

| Platform | Status |
|---|---|
| **Windows** (x64 and ARM64) | Supported. Tested on Windows 11. |
| **Linux** | Supported. Tested on Ubuntu, including Proton prefixes and Flatpak Steam. Bazzite and SteamOS-style distros are targets; reports welcome. |
| **macOS** | Runs, but used for development only. |

## Getting started

### Download

Get the latest version from the [Releases page](https://github.com/QPfixxy/RigSwap/releases) (the current one, 2.0.0a1, is an alpha):

- **Windows** (x64 or ARM64): run `RigSwap-…-windows-x64-setup.exe`. It installs just for you, without administrator rights.
- **Linux** (x86_64 or aarch64): download `RigSwap-…-linux-x86_64.AppImage`, make it executable (`chmod +x`), and run it. `RigSwap.AppImage cli <command>` runs the command line.

### From source

It needs Python 3.11 or newer.

```bash
git clone https://github.com/QPfixxy/RigSwap.git
cd RigSwap
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
rigswap gui
```

Once the app is open:

1. **Add your setups** with the **+** button, for example `Handheld` and `eGPU Dock`.
2. **Import your games** with **Import games**, or use **Add game…** for anything else. RigSwap finds each game's config files as it imports them (it asks once before downloading the game database).
3. **Check what it found** in the details panel. For games it couldn't place, use **Find automatically** or **Learn…**, or add files, folders or registry keys by hand.
4. **Save each setup.** Set the game up for one setup, then click **Save current** next to that setup. Repeat for the next one.
5. **Switch.** Click a setup at the top and every game is updated.
6. **Optional: switch automatically.** Right-click a setup, choose **Use automatically when…** (for example, *External GPU: Connected* for your dock), then turn on **Auto-switch**.

### Command line

Everything in the app also works from the `rigswap` command, which is handy for scripts and for gaming modes without a desktop:

```bash
rigswap setup add "Handheld"
rigswap import                                        # add installed games from every launcher
rigswap detect --all --add                            # find config files for every game
rigswap learn "Hollow Knight"                         # find settings by watching what changes
rigswap game add "Elden Ring" --exe eldenring.exe     # or add any game by hand
rigswap config add "Elden Ring" "%APPDATA%\EldenRing" --include "*.xml"
rigswap config add "Valheim" "HKCU\Software\IronGate\Valheim" --registry --exclude "*Save*"
rigswap save "Handheld" --all                         # save every game's current settings
rigswap switch "eGPU Dock"                            # apply every game's eGPU Dock settings
rigswap undo                                          # put back the configs from before the last switch
rigswap status                                        # which games changed since they were saved
rigswap hardware                                      # what RigSwap sees: GPUs, power, displays
rigswap setup when "eGPU Dock" --external-gpu yes     # use this setup automatically when docked
rigswap watch                                         # switch automatically (or turn on Auto-switch in the app)
rigswap autostart on                                  # start RigSwap when you log in
```

Run `rigswap --help` for the full list of commands.

## Where your data lives

Saved configs and backups are stored in your user data folder and never inside game folders:

- **Windows:** `%LOCALAPPDATA%\rigswap`
- **Linux:** `~/.local/share/rigswap`

Set `RIGSWAP_DATA_DIR` to use a different folder.

## Roadmap

- [x] **Phase 0:** Foundation: data model, storage, tests, CI on Windows and Linux
- [x] **Phase 1:** Manual switching: Steam discovery, safe swapping, desktop app
- [x] **Phase 2:** Automatic config detection, locked setups and change checks
- [x] **Phase 3:** Automatic switching when an eGPU is connected or disconnected, or on power and display changes
- [x] **Phase 4:** More launchers, registry settings, engine rules and Learn mode for games nothing else recognises
- [ ] **Phase 5:** Installers: Windows installer ✓, AppImage ✓, release workflow ✓, first release (2.0.0a1) ✓, Flatpak to come

See [ROADMAP.md](ROADMAP.md) for details.

## Development

```bash
pip install -e ".[dev]"
pytest              # unit, integration and GUI tests (set QT_QPA_PLATFORM=offscreen on a headless machine)
ruff check .        # lint
```

Building installers (see `packaging/`): `pip install -e ".[build]"`, then `packaging\windows\build.ps1` on Windows (needs [Inno Setup 6](https://jrsoftware.org/isinfo.php)) or `packaging/linux/build-appimage.sh` on Linux. Pushing a `vX.Y.Z` tag builds every package in GitHub Actions and creates a draft release.

```
src/rigswap/
  core/        data model, swapping, detection, engine rules, Learn mode, registry, auto-switching
  hardware/    what's connected: GPUs, power, displays (Windows and Linux)
  launchers/   finding installed games: Epic, GOG, Game Bar, Heroic, Lutris
  gui/         PySide6 desktop app
  cli.py       the rigswap command
tests/
```

Bug reports and pull requests are welcome.

The original v0.1 (PyQt5) is kept on the [`legacy`](https://github.com/QPfixxy/RigSwap/tree/legacy) branch.

## Related projects

- [Ludusavi](https://github.com/mtkennerly/ludusavi): game save backup. Its [manifest](https://github.com/mtkennerly/ludusavi-manifest), compiled from [PCGamingWiki](https://www.pcgamingwiki.com/), is the optional game database RigSwap can use. Missing or wrong paths can be fixed on PCGamingWiki and flow back to everyone.
- [GPUPrefSwitcher](https://github.com/sharpjd/GPUPrefSwitcher) and [Thunderbolt Switch](https://github.com/Valkirie/Thunderbolt-Switch): Windows tools that cover parts of the same problem.

## License

Copyright (C) 2025-2026 QPfixxy

RigSwap is free software: you can redistribute it and/or modify it under the terms of the [GNU General Public License](LICENSE), version 3 or (at your option) any later version. In short, you may use, share and change it, but any version you distribute must also be released as open source under the GPL. It comes with no warranty.
