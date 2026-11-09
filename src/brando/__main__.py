"""Frozen and source-mode entrypoint, including isolated engine dispatch."""
import sys

if len(sys.argv) > 1 and sys.argv[1] == "--engine-worker":
    from .engine_worker import main
    raise SystemExit(main(sys.argv[2]))
elif len(sys.argv) > 1 and sys.argv[1] == "--convert":
    from .cli import main
    raise SystemExit(main(sys.argv[2:]))
else:
    from .gui import main
    raise SystemExit(main())
