from __future__ import annotations

import sys
from collections.abc import Sequence

from ._cli_impl import DEVTOOLS_COMMANDS, main as compatibility_main
from .devtools_fixtures import (
    build_guarded_strict_verification_result_fixture as build_guarded_strict_verification_result_fixture,
)
from .redaction import (
    build_default_redaction_policy as build_default_redaction_policy,
    build_redaction_receipt as build_redaction_receipt,
    redact_prepared_spec as redact_prepared_spec,
    sanitize_public_artifact as sanitize_public_artifact,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] not in DEVTOOLS_COMMANDS:
        command = args[0] if args else 'missing'
        print(f'devtools_cli_rejects_kernel_command:{command}:use sclite', file=sys.stderr)
        return 2
    return compatibility_main(args, emit_deprecation=False)


if __name__ == '__main__':
    raise SystemExit(main())
