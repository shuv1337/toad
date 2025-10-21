import sys

import click
from toad.app import ToadApp


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Toad. The Batrachian AI."""
    if ctx.invoked_subcommand is not None:
        return
    app = ToadApp()
    app.run()


@main.command("acp")
@click.argument("command", metavar="COMMAND")
@click.option("--project-dir", metavar="PATH", default=None)
def acp(command: str, project_dir: str | None) -> None:
    """Run an ACP client."""
    app = ToadApp(acp_command=command, project_dir=project_dir)
    app.run()


@main.command("settings")
def settings() -> None:
    """Configure settings."""
    app = ToadApp()
    print(f"{app.settings_path}")


@main.command("replay")
@click.argument("path", metavar="PATH.jsonl")
def replay(path: str) -> None:
    """Replay interaction from a jsonl file."""
    import time

    stdout = sys.stdout.buffer
    with open(path, "rb") as replay_file:
        for line in replay_file.readlines():
            time.sleep(0.1)
            stdout.write(line)
            stdout.flush()


if __name__ == "__main__":
    main()
