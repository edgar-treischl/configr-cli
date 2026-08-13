from click.testing import CliRunner
from configr_cli.cli import main

def test_greeting():
    runner = CliRunner()
    result = runner.invoke(main, ["--name", "Test"])
    assert result.exit_code == 0
    assert "Hello, Test!" in result.output
