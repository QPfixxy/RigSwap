"""Start the desktop app: `rigswap gui` or `rigswap-gui`."""

from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from rigswap.core import instance
from rigswap.core.models import LibraryError
from rigswap.gui import icon_path, theme

APP_ID = "io.github.qpfixxy.RigSwap"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    instance.mark_running()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("RigSwap")
    app.setDesktopFileName(APP_ID)  # matches the .desktop file, so Linux shows our icon
    app.setWindowIcon(QIcon(icon_path("app.png")))
    theme.apply(app)

    from rigswap.gui.main_window import MainWindow
    from rigswap.gui.state import AppState

    try:
        state = AppState()
    except LibraryError as e:
        QMessageBox.critical(None, "RigSwap",
                             f"Your library file can't be read, so nothing was changed.\n\n{e}")
        return 1
    window = MainWindow(state)
    # At login (--tray) with automatic switching on, start quietly in the tray.
    if not ("--tray" in args and window.tray is not None and state.lib.settings.auto_switch):
        window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
