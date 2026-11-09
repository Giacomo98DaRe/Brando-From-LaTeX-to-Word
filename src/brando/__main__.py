"""Frozen and source-mode entrypoint, including isolated engine dispatch."""
import sys


def main() -> int:
    """Dispatch before importing Qt so isolated workers stay headless."""
    arguments = sys.argv[1:]
    if arguments and arguments[0] == "--engine-worker":
        from .engine_worker import main as run_worker
        return run_worker(arguments[1])
    if arguments and arguments[0] == "--convert":
        from .cli import main as run_cli
        return run_cli(arguments[1:])
    from .gui import main as run_gui
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
