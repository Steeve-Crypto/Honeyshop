"""Allow running with python -m honeyshop."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
