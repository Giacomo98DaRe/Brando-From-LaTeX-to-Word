"""PyInstaller wrapper for the shared application entry point."""

from brando.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
