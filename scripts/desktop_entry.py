"""PyInstaller entrypoint without requiring Qt initialization for worker processes."""
import sys

if len(sys.argv) > 1 and sys.argv[1] == "--engine-worker":
    from brando.engine_worker import main
    raise SystemExit(main(sys.argv[2]))
elif len(sys.argv) > 1 and sys.argv[1] == "--convert":
    from brando.cli import main
    raise SystemExit(main(sys.argv[2:]))
else:
    from brando.gui import main
    raise SystemExit(main())
