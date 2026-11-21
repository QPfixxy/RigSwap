"""Command-line interface: `rigswap switch "eGPU Dock"` and friends.

Games and setups are named on the command line by name (any case); games can also
be named by Steam app id or the start of their id (shown by `rigswap game list`).
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path

from rigswap import __version__
from rigswap.core.models import ConfigLocation, Game, Library, LibraryError, LocationKind, Setup
from rigswap.core.store import LibraryStore


class CliError(Exception):
    pass


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], int] | None = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    from rigswap.core.manifest import ManifestError
    from rigswap.core.swap import SwapError

    try:
        return handler(args)
    except (CliError, LibraryError, SwapError, ManifestError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rigswap", description="RigSwap")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    def cmd(parent, name, handler, help_text):
        p = parent.add_parser(name, help=help_text, description=help_text)
        p.set_defaults(handler=handler)
        return p

    cmd(sub, "info", _info, "show where data is stored and what's in the library")
    p = cmd(sub, "gui", _gui, "open the app window")
    p.add_argument("--tray", action="store_true",
                   help="start minimised to the tray (when automatic switching is on)")
    cmd(sub, "hardware", _hardware, "show the GPUs, power and displays RigSwap sees")

    p = cmd(sub, "import", _import,
            "find installed games from every launcher and add them to the library")
    p.add_argument("--list", action="store_true", help="only list what's found")
    p.add_argument("--include-found-by-windows", action="store_true",
                   help="also add games found only in Windows' own game list "
                        "(it can include non-games)")

    p = cmd(sub, "steam", _steam, "list installed Steam games")
    p.add_argument("--import", dest="do_import", action="store_true",
                   help="add them to the library")

    setup = sub.add_parser("setup", help="manage setups (Handheld, eGPU Dock, ...)")
    setup_sub = setup.add_subparsers(dest="action", metavar="ACTION", required=True)
    cmd(setup_sub, "list", _setup_list, "list setups (* = active)")
    p = cmd(setup_sub, "add", _setup_add, "add a setup")
    p.add_argument("name")
    p = cmd(setup_sub, "rename", _setup_rename, "rename a setup")
    p.add_argument("name")
    p.add_argument("new_name")
    p = cmd(setup_sub, "remove", _setup_remove, "remove a setup and its saved configs")
    p.add_argument("name")
    p.add_argument("--yes", action="store_true", help="also delete its saved configs")
    p = cmd(setup_sub, "lock", _setup_lock,
            "lock a setup: switching away never saves over its configs")
    p.add_argument("name")
    p = cmd(setup_sub, "unlock", _setup_unlock, "unlock a setup")
    p.add_argument("name")
    p = cmd(setup_sub, "when", _setup_when,
            "set when a setup is used automatically (all given conditions must hold)")
    p.add_argument("name")
    p.add_argument("--external-gpu", choices=["yes", "no", "any"],
                   help="an external GPU is (or isn't) connected")
    p.add_argument("--gpu", metavar="TEXT",
                   help="a connected GPU's name contains TEXT, e.g. 'RTX 4070' ('' to clear)")
    p.add_argument("--power", choices=["ac", "battery", "any"])
    p.add_argument("--display", choices=["yes", "no", "any"],
                   help="an external display is (or isn't) connected")
    p.add_argument("--clear", action="store_true", help="never switch to it automatically")
    p = cmd(setup_sub, "move", _setup_move,
            "change the order setups are checked in (1 = checked first)")
    p.add_argument("name")
    p.add_argument("position", type=int)

    game = sub.add_parser("game", help="manage games")
    game_sub = game.add_subparsers(dest="action", metavar="ACTION", required=True)
    cmd(game_sub, "list", _game_list, "list games")
    p = cmd(game_sub, "add", _game_add, "add a game by hand")
    p.add_argument("name")
    p.add_argument("--install-dir", help="the game's install folder (used to see if it's running)")
    p.add_argument("--exe", action="append", default=[], metavar="EXE",
                   help="game executable: full path or file name, e.g. eldenring.exe (repeatable)")
    p = cmd(game_sub, "show", _game_show, "show a game's details, config locations and snapshots")
    p.add_argument("game")
    p = cmd(game_sub, "edit", _game_edit, "change a game's name, install folder or executables")
    p.add_argument("game")
    p.add_argument("--name")
    p.add_argument("--install-dir")
    p.add_argument("--add-exe", action="append", default=[], metavar="EXE")
    p.add_argument("--remove-exe", action="append", default=[], metavar="EXE")
    p = cmd(game_sub, "remove", _game_remove, "remove a game and its saved configs")
    p.add_argument("game")
    p.add_argument("--yes", action="store_true", help="also delete its saved configs")

    config = sub.add_parser("config", help="manage a game's config files and folders")
    config_sub = config.add_subparsers(dest="action", metavar="ACTION", required=True)
    p = cmd(config_sub, "add", _config_add,
            "add a config file, folder or registry key to a game")
    p.add_argument("game")
    p.add_argument("path", help="a file or folder, or with --registry a key such as "
                                "HKCU\\Software\\Company\\Game")
    kind = p.add_mutually_exclusive_group()
    kind.add_argument("--registry", action="store_true",
                      help="it's a registry key (Windows, or inside the game's Wine prefix)")
    kind.add_argument("--file", action="store_true",
                      help="it's a file (needed if it doesn't exist yet)")
    kind.add_argument("--folder", action="store_true", help="it's a folder")
    p.add_argument("--include", action="append", default=[], metavar="GLOB",
                   help="folders and registry keys only: just these files or values, "
                        "e.g. '*.ini' (repeatable)")
    p.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                   help="folders and registry keys only: never these, e.g. 'saves/*' "
                        "(repeatable)")
    p = cmd(config_sub, "remove", _config_remove,
            "remove a config location (its number from rigswap game show)")
    p.add_argument("game")
    p.add_argument("number", type=int)

    p = cmd(sub, "save", _save, "save a game's current config as its snapshot for a setup")
    p.add_argument("setup")
    p.add_argument("game", nargs="?", help="omit with --all")
    p.add_argument("--all", action="store_true", help="every game that has config locations")

    p = cmd(sub, "switch", _switch, "apply every game's config for a setup")
    p.add_argument("setup")

    cmd(sub, "undo", _undo, "put back the configs from before the last switch")

    p = cmd(sub, "autostart", _autostart, "start RigSwap when you log in")
    p.add_argument("action", choices=["on", "off", "status"])
    p.add_argument("--headless", action="store_true",
                   help="Linux: run 'rigswap watch' as a background service instead of the app")

    p = cmd(sub, "watch", _watch,
            "switch setups automatically when the hardware changes (runs until stopped)")
    p.add_argument("--interval", type=float, default=3.0, help="seconds between checks")
    p.add_argument("--once", action="store_true", help="check once and exit")

    p = cmd(sub, "restore", _restore,
            "put a game's saved config back (for the active setup unless --setup)")
    p.add_argument("game")
    p.add_argument("--setup")

    cmd(sub, "status", _status, "list games whose live config differs from the active setup's")

    man = sub.add_parser("manifest", help="the game config database")
    man_sub = man.add_subparsers(dest="action", metavar="ACTION", required=True)
    cmd(man_sub, "update", _manifest_update, "download or update it (about 17 MB)")
    cmd(man_sub, "info", _manifest_info, "show whether it's downloaded and how big it is")

    p = cmd(sub, "learn", _learn,
            "find a game's settings by watching what changes while you change one in the game")
    p.add_argument("game")
    p.add_argument("--yes", action="store_true", help="add the likely ones without asking")

    p = cmd(sub, "detect", _detect, "find games' config files using the manifest")
    p.add_argument("game", nargs="?", help="omit with --all")
    p.add_argument("--all", action="store_true", help="every game in the library")
    p.add_argument("--add", action="store_true", help="add the safe ones it finds")
    return parser


# --- helpers ----------------------------------------------------------------------


def _open() -> tuple[LibraryStore, Library]:
    store = LibraryStore()
    return store, store.load()


def _find_setup(lib: Library, name: str) -> Setup:
    setup = lib.setup_by_name(name)
    if setup is None:
        names = ", ".join(s.name for s in lib.setups) or "none yet"
        raise CliError(f"no setup named {name!r} (setups: {names})")
    return setup


def _abspath(path: str) -> str:
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))


def _kind_word(kind: LocationKind) -> str:
    return {LocationKind.DIRECTORY: "folder", LocationKind.REGISTRY: "registry key"}.get(
        kind, "file")


def _active_name(lib: Library) -> str:
    active = lib.settings.active_setup_id
    return lib.setup(active).name if active else "-"


# --- info / steam -----------------------------------------------------------------


def _gui(args) -> int:
    from rigswap.gui.app import main as gui_main

    return gui_main(["--tray"] if args.tray else [])


def _hardware(args) -> int:
    from rigswap import hardware
    from rigswap.core import auto

    state = hardware.read_state()
    for line in state.describe():
        print(line)
    _, lib = _open()
    match = auto.choose_setup(lib, state)
    print("Matching setup: " + (match.name if match else "none"))
    return 0


def _info(args) -> int:
    store, lib = _open()
    print(f"Data folder: {store.root}")
    print(f"Setups: {len(lib.setups)}  Games: {len(lib.games)}  Active setup: {_active_name(lib)}")
    return 0


def _steam(args) -> int:
    from rigswap.core import steam

    installs = steam.find_steam_installs()
    if not installs:
        print("No Steam install found.")
        return 0
    for inst in installs:
        print(f"Steam: {inst.root}" + (" (Flatpak)" if inst.flatpak else ""))
        for lib_dir in steam.library_folders(inst.root):
            print(f"  Library: {lib_dir}")
    games = steam.discover_games(installs)
    for g in games:
        tag = " [Proton]" if g.uses_proton else ""
        print(f"{g.app_id:>9}  {g.name}{tag}")
    print(f"{len(games)} game(s)")
    if args.do_import:
        store, lib = _open()
        result = steam.import_games(lib, games)
        print(f"Imported: {len(result.added)} new, {len(result.updated)} updated")
        _detect_new(store, lib, result.added)
        store.save(lib)
    return 0


# --- setups -----------------------------------------------------------------------


def _setup_list(args) -> int:
    _, lib = _open()
    if not lib.setups:
        print('No setups yet. Add one with: rigswap setup add "Handheld"')
    for s in lib.setups:
        marker = "*" if s.id == lib.settings.active_setup_id else " "
        count = sum(1 for snap in lib.snapshots if snap.setup_id == s.id)
        lock = ", locked" if s.locked else ""
        print(f"{marker} {s.name}  ({count} game(s) saved{lock})")
    return 0


def _setup_add(args) -> int:
    store, lib = _open()
    setup = lib.add_setup(args.name)
    store.save(lib)
    print(f"Added setup {setup.name}.")
    return 0


def _setup_rename(args) -> int:
    store, lib = _open()
    setup = _find_setup(lib, args.name)
    old = setup.name
    lib.rename_setup(setup.id, args.new_name)
    store.save(lib)
    print(f"Renamed {old} to {setup.name}.")
    return 0


def _setup_remove(args) -> int:
    from rigswap.core import swap

    store, lib = _open()
    setup = _find_setup(lib, args.name)
    saved = sum(1 for snap in lib.snapshots if snap.setup_id == setup.id)
    if saved and not args.yes:
        raise CliError(f"{setup.name} has saved configs for {saved} game(s); "
                       "add --yes to delete them too")
    lib.remove_setup(setup.id)
    store.save(lib)
    swap.delete_setup_data(store.root, setup.id)
    print(f"Removed setup {setup.name}" + (f" and {saved} saved config(s)." if saved else "."))
    return 0


# --- games ------------------------------------------------------------------------


def _game_list(args) -> int:
    _, lib = _open()
    if not lib.games:
        print("No games yet. Import Steam games with: rigswap steam --import, "
              'or add one with: rigswap game add "Name"')
    for g in sorted(lib.games, key=lambda g: g.name.casefold()):
        source = (f"steam {g.steam_app_id}" if g.steam_app_id
                  else STORE_LABELS.get(g.store, g.store) if g.store else "manual")
        saved = [lib.setup(s.setup_id).name for s in lib.snapshots if s.game_id == g.id]
        print(f"{g.id[:8]}  {g.name}  [{source}]  "
              f"{len(g.config_locations)} config location(s)"
              + (f", saved for: {', '.join(saved)}" if saved else ""))
    return 0


def _game_add(args) -> int:
    store, lib = _open()
    game = Game(name=args.name.strip(),
                install_dir=_abspath(args.install_dir) if args.install_dir else None,
                executables=[_exe(e) for e in args.exe])
    lib.add_game(game)
    store.save(lib)
    print(f"Added {game.name} ({game.id[:8]}).")
    if not (game.install_dir or game.executables):
        print("Tip: give it --install-dir or --exe so switching can check it isn't running.")
    print(f'Next: rigswap config add "{game.name}" <path to its config file or folder>')
    return 0


def _exe(value: str) -> str:
    """Keep bare file names as they are; make paths absolute."""
    if "/" in value or "\\" in value or value.startswith("~"):
        return _abspath(value)
    return value


def _game_show(args) -> int:
    _, lib = _open()
    g = lib.find_game(args.game)
    print(f"{g.name}  (id {g.id})")
    if g.steam_app_id:
        print(f"  Steam app: {g.steam_app_id}")
    print(f"  Install folder: {g.install_dir or '-'}")
    if g.store and g.store not in ("steam",):
        print(f"  Store: {g.store}" + (f" ({g.store_id})" if g.store_id else ""))
    if g.wine_prefix:
        print(f"  Wine prefix: {g.wine_prefix}")
    print(f"  Executables: {', '.join(g.executables) or '-'}")
    print("  Config locations:" + ("" if g.config_locations else " none"))
    for n, loc in enumerate(g.config_locations, 1):
        line = f"    {n}. [{_kind_word(loc.kind)}] {loc.path}"
        if loc.kind != LocationKind.REGISTRY and not Path(loc.path).exists():
            line += "  (doesn't exist yet)"
        if loc.include:
            line += f"  include {', '.join(loc.include)}"
        if loc.exclude:
            line += f"  exclude {', '.join(loc.exclude)}"
        print(line)
    snaps = [s for s in lib.snapshots if s.game_id == g.id]
    print("  Saved for:" + ("" if snaps else " no setups yet"))
    for s in snaps:
        print(f"    {lib.setup(s.setup_id).name}: {s.saved_at.astimezone():%Y-%m-%d %H:%M}")
    return 0


def _game_edit(args) -> int:
    store, lib = _open()
    g = lib.find_game(args.game)
    if args.name is not None:
        if not args.name.strip():
            raise CliError("the name can't be empty")
        g.name = args.name.strip()
    if args.install_dir is not None:
        g.install_dir = _abspath(args.install_dir) if args.install_dir else None
    for e in args.add_exe:
        if _exe(e) not in g.executables:
            g.executables.append(_exe(e))
    for e in args.remove_exe:
        if _exe(e) not in g.executables:
            raise CliError(f"{g.name} has no executable {e!r}")
        g.executables.remove(_exe(e))
    store.save(lib)
    print(f"Updated {g.name}.")
    return 0


def _game_remove(args) -> int:
    from rigswap.core import swap

    store, lib = _open()
    g = lib.find_game(args.game)
    saved = sum(1 for s in lib.snapshots if s.game_id == g.id)
    if saved and not args.yes:
        raise CliError(f"{g.name} has saved configs for {saved} setup(s); "
                       "add --yes to delete them too")
    lib.remove_game(g.id)
    store.save(lib)
    swap.delete_game_data(store.root, g.id)
    print(f"Removed {g.name}.")
    return 0


# --- config locations -----------------------------------------------------------


def _config_add(args) -> int:
    store, lib = _open()
    g = lib.find_game(args.game)
    if args.registry:
        from rigswap.core import detect, registry

        try:
            key = registry.normalize_key(args.path)
        except registry.RegistryError as e:
            raise CliError(str(e)) from e
        backend = detect.registry_backend(g)
        if backend is None:
            raise CliError(f"{g.name} has no registry here: registry keys work on Windows, "
                           "or for games that run in a Wine/Proton prefix")
        loc = ConfigLocation(key, LocationKind.REGISTRY, include=args.include,
                             exclude=args.exclude)
        lib.add_config_location(g.id, loc)
        store.save(lib)
        note = "" if backend.exists(key) else " (it doesn't exist yet)"
        print(f"Added registry key {key} to {g.name}{note}.")
        _warn_stale(lib, g)
        return 0
    path = Path(_abspath(args.path))
    if args.folder:
        kind = LocationKind.DIRECTORY
    elif args.file:
        kind = LocationKind.FILE
    elif path.is_dir():
        kind = LocationKind.DIRECTORY
    elif path.is_file():
        kind = LocationKind.FILE
    else:
        raise CliError(f"{path} doesn't exist; add --file or --folder to say which it will be")
    if kind == LocationKind.DIRECTORY and path.is_file():
        raise CliError(f"{path} is a file, not a folder")
    if kind == LocationKind.FILE and path.is_dir():
        raise CliError(f"{path} is a folder, not a file")
    if kind == LocationKind.FILE and (args.include or args.exclude):
        raise CliError("--include and --exclude only apply to folders")
    loc = ConfigLocation(str(path), kind, include=args.include, exclude=args.exclude)
    lib.add_config_location(g.id, loc)
    store.save(lib)
    print(f"Added {_kind_word(kind)} {path} to {g.name}.")
    _warn_stale(lib, g)
    return 0


def _config_remove(args) -> int:
    store, lib = _open()
    g = lib.find_game(args.game)
    loc = lib.remove_config_location(g.id, args.number - 1)
    store.save(lib)
    print(f"Removed {loc.path} from {g.name}. The file itself wasn't touched.")
    _warn_stale(lib, g)
    return 0


def _warn_stale(lib: Library, g: Game) -> None:
    names = [lib.setup(s.setup_id).name for s in lib.snapshots if s.game_id == g.id]
    if names:
        print(f"Note: {g.name}'s saved configs ({', '.join(names)}) were made with the old "
              "locations; switching skips them until you save them again.")


# --- save / switch / undo --------------------------------------------------------


def _save(args) -> int:
    from rigswap.core import swap

    store, lib = _open()
    setup = _find_setup(lib, args.setup)
    if args.all == bool(args.game):
        raise CliError("name one game, or use --all")
    games = [g for g in lib.games if g.config_locations] if args.all else [lib.find_game(args.game)]
    if not games:
        raise CliError("no games have config locations yet")
    for g in games:
        swap.save_snapshot(store.root, lib, g, setup.id)
        print(f"Saved {g.name} for {setup.name}.")
    store.save(lib)
    return 0


def _switch(args) -> int:
    from rigswap.core import swap

    store, lib = _open()
    setup = _find_setup(lib, args.setup)
    try:
        result = swap.switch_setup(store.root, lib, setup.id)
    except swap.SwapError as e:
        raise CliError(f"nothing changed: {e}") from e
    except OSError as e:
        raise CliError(f"switch failed and was rolled back: {e}") from e
    store.save(lib)
    print(f"Switched to {setup.name}: {len(result.applied)} game(s) applied, "
          f"{len(result.saved)} saved, {len(result.without_snapshot)} without a snapshot.")
    for g in result.stale:
        print(f"Skipped {g.name}: its config locations changed since it was saved for "
              f'{setup.name}. Run: rigswap save "{setup.name}" "{g.name}"')
    for g in result.unchecked:
        print(f"Warning: couldn't check whether {g.name} was running "
              "(give it --install-dir or --exe with rigswap game edit).")
    return 0


def _undo(args) -> int:
    from rigswap.core import swap

    store, lib = _open()
    result = swap.undo_last(store.root, lib)
    if result is None:
        print("Nothing to undo.")
        return 0
    store.save(lib)
    print(f"Undone: {len(result.restored)} game(s) restored. Active setup: {_active_name(lib)}")
    return 0


# --- locked setups, restore, status --------------------------------------------------


def _setup_lock(args) -> int:
    return _set_locked(args.name, True)


def _setup_unlock(args) -> int:
    return _set_locked(args.name, False)


def _set_locked(name: str, locked: bool) -> int:
    store, lib = _open()
    setup = _find_setup(lib, name)
    setup.locked = locked
    store.save(lib)
    if locked:
        print(f"Locked {setup.name}: switching away won't save over its configs. "
              f"'rigswap save' still updates them when you ask.")
    else:
        print(f"Unlocked {setup.name}.")
    return 0


def _restore(args) -> int:
    from rigswap.core import swap

    store, lib = _open()
    game = lib.find_game(args.game)
    setup = _find_setup(lib, args.setup) if args.setup else (
        lib.setup(lib.settings.active_setup_id) if lib.settings.active_setup_id else None)
    if setup is None:
        raise CliError("no active setup; name one with --setup")
    try:
        swap.restore_game(store.root, lib, game, setup.id)
    except OSError as e:
        raise CliError(f"restore failed and was rolled back: {e}") from e
    print(f"Put back {game.name}'s saved {setup.name} config. 'rigswap undo' reverses this.")
    return 0


def _status(args) -> int:
    from rigswap.core import swap

    store, lib = _open()
    active = lib.settings.active_setup_id
    if not active:
        print("No active setup yet.")
        return 0
    setup = lib.setup(active)
    lock = " (locked)" if setup.locked else ""
    print(f"Active setup: {setup.name}{lock}")
    any_changed = False
    for g in sorted(lib.games, key=lambda g: g.name.casefold()):
        changed = swap.changed_files(store.root, lib, g, active)
        if changed:
            any_changed = True
            print(f"  {g.name}: {len(changed)} file(s) differ from the saved {setup.name} config")
            for path in changed[:5]:
                print(f"      {path}")
    if not any_changed:
        print("  Every game matches its saved config.")
    elif setup.locked:
        print(f"{setup.name} is locked, so these changes won't be saved. "
              "Put a game back with: rigswap restore <game>")
    else:
        print(f"These changes are saved into {setup.name} when you switch away.")
    return 0


# --- manifest / detection -------------------------------------------------------------


def _manifest_update(args) -> int:
    from rigswap.core import manifest

    store, lib = _open()
    print("Checking for game config database updates...")
    result = manifest.update(store.root)
    if lib.settings.use_manifest is not True:
        lib.settings.use_manifest = True
        store.save(lib)
    print(("Downloaded" if result.changed else "Already up to date:")
          + f" {result.games} games with known config files.")
    return 0


def _manifest_info(args) -> int:
    from rigswap.core import manifest

    store, _ = _open()
    man = manifest.load(store.root)
    if man is None:
        print("Not downloaded yet. Run: rigswap manifest update")
    else:
        print(f"{len(man)} games with known config files, downloaded {man.fetched_at}.")
    return 0


def _detect(args) -> int:
    from rigswap.core import detect, manifest

    store, lib = _open()
    man = manifest.load(store.root) if lib.settings.use_manifest is not False else None
    if man is None:
        print("Using engine rules only (the game config database isn't downloaded; "
              "'rigswap manifest update' gets it).")
    if args.all == bool(args.game):
        raise CliError("name one game, or use --all")
    games = sorted(lib.games, key=lambda g: g.name.casefold()) if args.all \
        else [lib.find_game(args.game)]
    total_added = 0
    for g in games:
        found = detect.detect_game(g, man)
        if found is None:
            if not args.all:
                print(f"{g.name}: not in the game config database, and its engine isn't "
                      "recognised. Add its config files by hand.")
            continue
        new = detect.new_locations(g, found)
        if not (new or found.mixed or found.mixed_registry or found.registry
                or found.missing or found.notes) and args.all:
            continue
        print(f"{g.name}  ({detect.sources(found)})")
        for loc in new:
            print(f"  + {_kind_word(loc.kind)}: {loc.path}")
        for path in [*found.mixed, *found.mixed_registry]:
            print(f"  ? also holds saves, not added: {path}")
        for key in found.registry:
            print(f"  ! settings in the registry, which can't be swapped on this computer: "
                  f"{key}")
        for path in found.missing:
            print(f"  - not there yet (launch the game once): {path}")
        for note in found.notes:
            print(f"  note: {note}")
        if not new and not found.mixed and not found.mixed_registry:
            print("  nothing new to add")
        if args.add and new:
            detect.add_detected(lib, g, found)
            total_added += len(new)
    if args.add:
        store.save(lib)
        print(f"Added {total_added} config location(s).")
    elif any(detect.new_locations(g, f) for g in games if (f := detect.detect_game(g, man))):
        print("Run again with --add to add the files marked +.")
    return 0


# --- automatic switching -----------------------------------------------------------


def _describe_when(setup: Setup) -> str:
    return setup.when.describe()


def _setup_when(args) -> int:
    from rigswap.core.models import Conditions, Power

    store, lib = _open()
    setup = _find_setup(lib, args.name)
    if args.clear:
        setup.when = Conditions()
    else:
        w = setup.when
        yes_no = {"yes": True, "no": False, "any": None}
        if args.external_gpu:
            w.external_gpu = yes_no[args.external_gpu]
        if args.gpu is not None:
            w.gpu_name = args.gpu.strip() or None
        if args.power:
            w.power = None if args.power == "any" else Power(args.power)
        if args.display:
            w.external_display = yes_no[args.display]
    store.save(lib)
    print(f"{setup.name} is used automatically when: {_describe_when(setup)}.")
    return 0


def _setup_move(args) -> int:
    store, lib = _open()
    setup = _find_setup(lib, args.name)
    lib.move_setup(setup.id, args.position - 1)
    store.save(lib)
    for i, s in enumerate(lib.setups, 1):
        print(f"{i}. {s.name}: {_describe_when(s)}")
    return 0


def _watch(args) -> int:
    import time

    from rigswap.core import instance

    instance.mark_running()  # installers then ask to close it first

    from rigswap import hardware
    from rigswap.core import auto, swap

    store = LibraryStore()
    lib_box: dict[str, Library] = {}

    def get_library() -> Library:
        lib_box["lib"] = store.load()  # pick up changes made in the app or other commands
        return lib_box["lib"]

    def do_switch(setup: Setup) -> swap.SwitchResult:
        lib = lib_box["lib"]
        result = swap.switch_setup(store.root, lib, setup.id)
        store.save(lib)
        return result

    switcher = auto.AutoSwitcher(get_library, do_switch, hardware.read_state,
                                 settle_ticks=1 if args.once else 2)
    lib = get_library()
    hint = "set some with: rigswap setup when <setup> --external-gpu yes"
    if not any(not s.when.is_empty() for s in lib.setups):
        if args.once:
            raise CliError(f"no setup has conditions yet; {hint}")
        # Keep running (e.g. as a login service): conditions added later are picked up.
        print(f"No setup has conditions yet, so nothing will switch until you {hint}.",
              flush=True)
    print("Watching hardware (Ctrl+C to stop). Setups, checked in this order:", flush=True)
    for s in lib.setups:
        print(f"  {s.name}: {_describe_when(s)}", flush=True)
    try:
        while True:
            event = switcher.tick()
            if isinstance(event, auto.Switched):
                r = event.result
                print(f"Switched to {event.setup.name}: {len(r.applied)} game(s) updated.",
                      flush=True)
            elif isinstance(event, auto.Waiting):
                names = ", ".join(g.name for g in event.games)
                print(f"Hardware matches {event.setup.name}; waiting for {names} to close.",
                      flush=True)
            elif isinstance(event, auto.Failed):
                print(f"Couldn't switch to {event.setup.name}: {event.error}", flush=True)
            if args.once:
                return 0
            time.sleep(max(0.5, args.interval))
    except KeyboardInterrupt:
        print("Stopped.")
        return 0


def _autostart(args) -> int:
    from rigswap.core import autostart

    if args.action == "status":
        on = autostart.is_enabled(args.headless)
        print("Starts at login: " + ("yes" if on else "no"))
        return 0
    try:
        print(autostart.set_enabled(args.action == "on", args.headless))
    except OSError as e:
        raise CliError(str(e)) from e
    return 0


STORE_LABELS = {"steam": "Steam", "epic": "Epic Games", "gog": "GOG", "amazon": "Amazon Games",
                "lutris": "Lutris", "gamebar": "found by Windows"}


def _import(args) -> int:
    from rigswap import launchers

    store, lib = _open()
    found = launchers.discover()
    if not found:
        print("No installed games found.")
        return 0
    chosen = []
    for g in found:
        have = launchers.is_in_library(lib, g)
        take = not have and (g.suggested or args.include_found_by_windows)
        mark = "=" if have else ("+" if take else " ")
        prefix = " [Wine]" if g.wine_prefix and g.store != "steam" else (
            " [Proton]" if g.wine_prefix else "")
        print(f"{mark} {g.name}  ({STORE_LABELS.get(g.store, g.store)}){prefix}")
        if take:
            chosen.append(g)
    print("(= already in the library, + new)")
    if args.list:
        return 0
    result = launchers.import_games(lib, chosen)
    print(f"Imported: {len(result.added)} new game(s).")
    skipped = sum(1 for g in found if g.store == "gamebar" and not launchers.is_in_library(lib, g))
    if skipped:
        print(f"{skipped} game(s) found only by Windows were left out; add them with "
              "--include-found-by-windows.")
    _detect_new(store, lib, result.added)
    store.save(lib)
    return 0


def _detect_new(store, lib, added) -> None:
    if not added:
        return
    from rigswap.core import detect, manifest

    man = manifest.load(store.root) if lib.settings.use_manifest is not False else None
    if man is None and lib.settings.use_manifest is not False:
        print("Tip: 'rigswap manifest update' downloads the game config database, so RigSwap "
              "finds config files for many more games.")
    n = 0
    for g in added:
        found = detect.detect_game(g, man)
        if found:
            n += bool(detect.add_detected(lib, g, found))
    print(f"Found config files for {n} of {len(added)} new game(s).")


def _learn(args) -> int:
    from rigswap.core import learn

    store, lib = _open()
    g = lib.find_game(args.game)
    print("Scanning where games keep their settings (before)...", flush=True)
    before = learn.scan(g)
    print(f"Now start {g.name}, change one graphics setting (resolution is a good one), "
          "apply it, then quit the game. Many games only save their settings when they close.")
    input("Press Enter when you've quit the game... ")
    print("Scanning again (after)...", flush=True)
    after = learn.scan(g)
    found = learn.suggestions(g, before, after)
    if after.partial:
        print("Note: there were so many files that the scan stopped early.")
    if not found:
        print("Nothing changed. Make sure the setting was applied and the game was closed, "
              "then try again.")
        return 0
    for i, s in enumerate(found, 1):
        mark = "x" if s.likely else " "
        print(f"{i:>3}. [{mark}] {_kind_word(s.location.kind)}: {s.location.path}  ({s.reason})")
    if args.yes:
        chosen = [s for s in found if s.likely]
    else:
        answer = input("Add which? Enter = the ticked ones, 'all', 'none', or numbers "
                       "like '1 3': ").strip().lower()
        if answer in ("", "y", "yes"):
            chosen = [s for s in found if s.likely]
        elif answer == "all":
            chosen = found
        elif answer in ("n", "no", "none"):
            chosen = []
        else:
            picks = {int(x) for x in answer.replace(",", " ").split() if x.isdigit()}
            chosen = [s for i, s in enumerate(found, 1) if i in picks]
    for s in chosen:
        lib.add_config_location(g.id, s.location)
    store.save(lib)
    print(f"Added {len(chosen)} config location(s) to {g.name}.")
    if chosen:
        _warn_stale(lib, g)
    return 0
