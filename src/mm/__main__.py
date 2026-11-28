"""Entry point for `python -m mm`: evaluate the agent and print the summary (see mm.eval.cli)."""

from mm.eval.cli import main

__all__ = ["main"]

if __name__ == "__main__":
    main()
