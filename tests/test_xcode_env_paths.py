"""Agent settings resolve a single repository-root `.env` path."""

from pathlib import Path

from tests.load_agent_settings import load_agent_settings_module

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_xcode_env_file_paths_default_points_at_repo_root():
    mod = load_agent_settings_module()
    paths = mod.xcode_env_file_paths()
    assert len(paths) == 1
    assert Path(paths[0]).resolve() == (_REPO_ROOT / ".env").resolve()


def test_xcode_env_file_paths_respects_xcode_env_file(tmp_path, monkeypatch):
    mod = load_agent_settings_module()

    custom = tmp_path / "custom.env"
    custom.write_text("FOO=bar\n")

    monkeypatch.setenv("XCODE_ENV_FILE", str(custom))
    assert mod.xcode_env_file_paths() == (str(custom),)

    monkeypatch.setenv("XCODE_ENV_FILE", str(tmp_path / "missing.env"))
    assert mod.xcode_env_file_paths() == (str(_REPO_ROOT / ".env"),)
