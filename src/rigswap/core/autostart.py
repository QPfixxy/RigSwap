"""Start RigSwap when the user logs in, so automatic switching keeps working.

- Windows: a value in the user's own Run key (HKCU\\...\\CurrentVersion\\Run). No admin
  needed; it shows up (and can be turned off) in Task Manager's Startup apps.
- Linux desktop: ~/.config/autostart/rigswap.desktop (the XDG autostart standard),
  starting the app minimised to the tray.
- Linux headless (e.g. a gaming session with no tray): a systemd user service that runs
  `rigswap watch`.
"""

from __future__ import annotations

import contextlib
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "RigSwap"
SERVICE_NAME = "rigswap-watch.service"


def gui_command(env: dict[str, str] | None = None) -> list[str]:
    """How to start the app in the tray, for however RigSwap was installed."""
    env = dict(os.environ) if env is None else env
    if env.get("APPIMAGE"):  # the AppImage file itself, not its temporary mount
        return [env["APPIMAGE"], "--tray"]
    if env.get("FLATPAK_ID"):
        return ["flatpak", "run", env["FLATPAK_ID"], "--tray"]
    bindir = Path(sys.executable).parent
    if getattr(sys, "frozen", False):  # a packaged build: the app sits next to us
        for name in ("RigSwap.exe", "RigSwap"):
            if (bindir / name).is_file():
                return [str(bindir / name), "--tray"]
    for name in ("rigswap-gui.exe", "rigswap-gui"):
        exe = bindir / name
        if exe.is_file():
            return [str(exe), "--tray"]
    found = shutil.which("rigswap-gui")
    if found:
        return [found, "--tray"]
    return [sys.executable, "-m", "rigswap", "gui", "--tray"]


def watch_command(env: dict[str, str] | None = None) -> list[str]:
    env = dict(os.environ) if env is None else env
    if env.get("APPIMAGE"):
        return [env["APPIMAGE"], "cli", "watch"]
    bindir = Path(sys.executable).parent
    names = ("rigswap-cli.exe", "rigswap-cli") if getattr(sys, "frozen", False) else (
        ("rigswap.exe",) if os.name == "nt" else ("rigswap",))
    for name in names:
        if (bindir / name).is_file():
            return [str(bindir / name), "watch"]
    return [sys.executable, "-m", "rigswap", "watch"]


# --- Windows -------------------------------------------------------------------------


def _windows_cmdline(cmd: list[str]) -> str:
    return subprocess.list2cmdline(cmd)


def windows_enabled(winreg: ModuleType | None = None) -> bool:
    winreg = winreg or _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except OSError:
        return False


def windows_set(enabled: bool, winreg: ModuleType | None = None,
                command: list[str] | None = None) -> None:
    winreg = winreg or _winreg()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ,
                              _windows_cmdline(command or gui_command()))
        else:
            with contextlib.suppress(FileNotFoundError):
                winreg.DeleteValue(key, VALUE_NAME)


def _winreg() -> ModuleType:
    import winreg

    return winreg


# --- Linux ---------------------------------------------------------------------------


def _config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def desktop_file(config_home: Path | None = None) -> Path:
    return (config_home or _config_home()) / "autostart" / "rigswap.desktop"


def service_file(config_home: Path | None = None) -> Path:
    return (config_home or _config_home()) / "systemd" / "user" / SERVICE_NAME


def linux_desktop_set(enabled: bool, config_home: Path | None = None,
                      command: list[str] | None = None) -> Path:
    path = desktop_file(config_home)
    if not enabled:
        path.unlink(missing_ok=True)
        return path
    exec_line = " ".join(shlex.quote(part) for part in (command or gui_command()))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=RigSwap\n"
        "Comment=Switch game graphics settings when your hardware changes\n"
        f"Exec={exec_line}\n"
        "Icon=io.github.qpfixxy.RigSwap\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
    )
    return path


def linux_service_set(enabled: bool, config_home: Path | None = None,
                      command: list[str] | None = None,
                      systemctl: list[str] | None = None) -> Path:
    """Write (or remove) the systemd user service and enable/disable it."""
    path = service_file(config_home)
    run = systemctl if systemctl is not None else ["systemctl", "--user"]
    if enabled:
        exec_line = " ".join(shlex.quote(part) for part in (command or watch_command()))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "[Unit]\n"
            "Description=RigSwap automatic setup switching\n"
            "After=graphical-session.target\n\n"
            "[Service]\n"
            f"ExecStart={exec_line}\n"
            "Restart=on-failure\n"
            "RestartSec=10\n\n"
            "[Install]\n"
            "WantedBy=default.target\n",
            encoding="utf-8",
        )
        if run:
            subprocess.run([*run, "daemon-reload"], check=False)
            subprocess.run([*run, "enable", "--now", SERVICE_NAME], check=False)
    else:
        if run and path.exists():
            subprocess.run([*run, "disable", "--now", SERVICE_NAME], check=False)
        path.unlink(missing_ok=True)
        if run:
            subprocess.run([*run, "daemon-reload"], check=False)
    return path


# --- one entry point -----------------------------------------------------------------


def is_enabled(headless: bool = False) -> bool:
    if sys.platform == "win32":
        return windows_enabled()
    return (service_file() if headless else desktop_file()).is_file()


def set_enabled(enabled: bool, headless: bool = False) -> str:
    """Turn start-at-login on or off; returns a short description of what was done."""
    if sys.platform == "win32":
        windows_set(enabled)
        return ("RigSwap starts in the tray when you sign in to Windows."
                if enabled else "RigSwap no longer starts with Windows.")
    if sys.platform.startswith("linux"):
        if headless:
            path = linux_service_set(enabled)
            return (f"Background service enabled ({path}); it runs 'rigswap watch' at login."
                    if enabled else "Background service removed.")
        path = linux_desktop_set(enabled)
        return (f"RigSwap starts in the tray when you log in ({path})."
                if enabled else "RigSwap no longer starts at login.")
    raise OSError("starting at login is only supported on Windows and Linux")
