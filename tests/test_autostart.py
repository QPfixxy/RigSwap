"""Start-at-login, tested against temp folders and a fake registry only."""

from types import SimpleNamespace

from rigswap.core import autostart


class FakeKey:
    def __init__(self, store):
        self.store = store

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_winreg():
    store: dict[str, str] = {}

    def open_key(hive, path):
        if path != autostart.RUN_KEY:
            raise OSError
        return FakeKey(store)

    def query(key, name):
        if name not in key.store:
            raise FileNotFoundError
        return key.store[name], 1

    def delete(key, name):
        if name not in key.store:
            raise FileNotFoundError
        del key.store[name]

    return SimpleNamespace(
        HKEY_CURRENT_USER="HKCU", REG_SZ=1, OpenKey=open_key, CreateKey=open_key,
        QueryValueEx=query, DeleteValue=delete,
        SetValueEx=lambda key, name, _r, _t, value: key.store.__setitem__(name, value),
        store=store)


def test_windows_run_key():
    reg = fake_winreg()
    assert not autostart.windows_enabled(reg)
    autostart.windows_set(True, reg, ["C:\\Program Files\\RigSwap\\rigswap-gui.exe", "--tray"])
    assert reg.store["RigSwap"] == '"C:\\Program Files\\RigSwap\\rigswap-gui.exe" --tray'
    assert autostart.windows_enabled(reg)
    autostart.windows_set(False, reg)
    autostart.windows_set(False, reg)  # already off: fine
    assert not autostart.windows_enabled(reg)


def test_linux_desktop_entry(tmp_path):
    path = autostart.linux_desktop_set(True, tmp_path, ["/home/me/.venv/bin/rigswap-gui",
                                                        "--tray"])
    text = path.read_text()
    assert path == tmp_path / "autostart" / "rigswap.desktop"
    assert "Exec=/home/me/.venv/bin/rigswap-gui --tray" in text and "Type=Application" in text
    autostart.linux_desktop_set(False, tmp_path)
    assert not path.exists()


def test_linux_service_quotes_paths_and_calls_systemctl(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(autostart.subprocess, "run", lambda cmd, check: calls.append(cmd))
    path = autostart.linux_service_set(True, tmp_path, ["/opt/my games/rigswap", "watch"],
                                       systemctl=["systemctl", "--user"])
    assert "ExecStart='/opt/my games/rigswap' watch" in path.read_text()
    assert ["systemctl", "--user", "enable", "--now", "rigswap-watch.service"] in calls
    autostart.linux_service_set(False, tmp_path, systemctl=["systemctl", "--user"])
    assert not path.exists()
    assert ["systemctl", "--user", "disable", "--now", "rigswap-watch.service"] in calls


def test_commands_fall_back_to_python_m(monkeypatch, tmp_path):
    monkeypatch.setattr(autostart.sys, "executable", str(tmp_path / "python"))
    monkeypatch.setattr(autostart.shutil, "which", lambda name: None)
    assert autostart.gui_command() == [str(tmp_path / "python"), "-m", "rigswap", "gui",
                                       "--tray"]
    assert autostart.watch_command()[-2:] == ["rigswap", "watch"]


def test_packaged_builds_start_the_right_thing(monkeypatch, tmp_path):
    assert autostart.gui_command({"APPIMAGE": "/home/me/Apps/RigSwap.AppImage"}) == \
        ["/home/me/Apps/RigSwap.AppImage", "--tray"]
    assert autostart.watch_command({"APPIMAGE": "/a/RigSwap.AppImage"}) == \
        ["/a/RigSwap.AppImage", "cli", "watch"]
    assert autostart.gui_command({"FLATPAK_ID": "io.github.qpfixxy.RigSwap"}) == \
        ["flatpak", "run", "io.github.qpfixxy.RigSwap", "--tray"]
    install = tmp_path / "RigSwap"
    install.mkdir()
    (install / "RigSwap.exe").write_text("")
    monkeypatch.setattr(autostart.sys, "executable", str(install / "rigswap.exe"))
    monkeypatch.setattr(autostart.sys, "frozen", True, raising=False)
    assert autostart.gui_command({}) == [str(install / "RigSwap.exe"), "--tray"]
