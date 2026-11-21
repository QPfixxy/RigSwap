# PyInstaller build: two programs sharing one folder (dist/RigSwap/).
#
#   RigSwap(.exe)      the app, without a console window
#   rigswap-cli(.exe)  the command line
#
# The command line isn't called "rigswap": on Windows (and macOS) file names ignore
# case, so it would clash with RigSwap.exe. The Windows installer adds a small
# bin\rigswap.cmd so people still type "rigswap"; the AppImage runs it as
# "RigSwap.AppImage cli ...".
#
# Build from the repository root:  pyinstaller --noconfirm packaging/pyinstaller/rigswap.spec

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]  # noqa: F821 (SPECPATH is set by PyInstaller)
ICON = str(ROOT / "docs" / "logo" / "rigswap.ico") if sys.platform == "win32" else None

datas = collect_data_files("rigswap")  # the app's icons
hidden = collect_submodules("rigswap")  # modules imported only when needed (launchers, ...)


def analysis(script):
    return Analysis(  # noqa: F821
        [str(ROOT / "packaging" / "pyinstaller" / script)],
        pathex=[str(ROOT / "src")],
        datas=datas,
        hiddenimports=hidden,
        excludes=["tkinter", "pytest", "pytestqt"],
    )


gui = analysis("gui_entry.py")
cli = analysis("cli_entry.py")

gui_exe = EXE(  # noqa: F821
    PYZ(gui.pure),  # noqa: F821
    gui.scripts,
    [],
    exclude_binaries=True,
    name="RigSwap",
    console=False,
    icon=ICON,
)
cli_exe = EXE(  # noqa: F821
    PYZ(cli.pure),  # noqa: F821
    cli.scripts,
    [],
    exclude_binaries=True,
    name="rigswap-cli",
    console=True,
    icon=ICON,
)
COLLECT(  # noqa: F821
    gui_exe, gui.binaries, gui.datas,
    cli_exe, cli.binaries, cli.datas,
    name="RigSwap",
)
