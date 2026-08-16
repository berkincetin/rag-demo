"""The launcher that makes the Next.js UI a single command.

`scripts/run_web.py` starts the API and the front-end together. Only its
decisions are tested here — the subprocess spawning itself is the thin part.
"""

from pathlib import Path

from scripts.run_web import api_command, needs_npm_install, web_command


def test_api_command_binds_the_configured_port():
    assert api_command(port=8000)[:3] == ["uvicorn", "src.rag.api:app", "--host"]
    assert "8000" in api_command(port=8000)


def test_api_command_honours_a_custom_port():
    assert "9001" in api_command(port=9001)


def test_web_command_runs_the_dev_server():
    assert web_command(dev=True) == ["npm", "run", "dev"]


def test_web_command_runs_the_built_server_in_production():
    # `npm start` serves the production build; using it without a build would
    # fail, so the launcher builds first (covered by needs_npm_install/build).
    assert web_command(dev=False) == ["npm", "start"]


def test_needs_npm_install_when_node_modules_is_absent(tmp_path: Path):
    assert needs_npm_install(tmp_path) is True


def test_no_npm_install_when_node_modules_exists(tmp_path: Path):
    (tmp_path / "node_modules").mkdir()

    assert needs_npm_install(tmp_path) is False
