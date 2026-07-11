from __future__ import annotations

import sys
from collections.abc import Sequence

from .cli import DEVTOOLS_COMMANDS, main as compatibility_main


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if args and args[0] in DEVTOOLS_COMMANDS:
        print(f'kernel_cli_rejects_devtool:{args[0]}:use sclite-devtools', file=sys.stderr)
        return 2
    return compatibility_main(args)
