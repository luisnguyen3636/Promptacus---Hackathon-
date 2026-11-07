"""Package entrypoint when invoked via `python -m urbansoc`."""

import sys
from urbansoc.cli import main

if __name__ == "__main__":
    sys.exit(main())
