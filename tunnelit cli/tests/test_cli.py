import pytest
from typer.testing import CliRunner
from tunnel_it.cli import app

runner = CliRunner()

def test_cli_invalid_port():
    result = runner.invoke(app, ["expose", "70000"])
    assert result.exit_code != 0

def test_cli_invalid_arg():
    result = runner.invoke(app, ["expose", "abc"])
    assert result.exit_code != 0
