"""Native exec flags forwarded without reconstructing Codex configuration."""

BOOLEAN_FLAGS = (
    '--strict-config', '--oss', '--ephemeral', '--ignore-user-config',
    '--ignore-rules', '--dangerously-bypass-hook-trust',
)
VALUE_FLAGS = ('--local-provider', '--thread-source', '--cyber-access-program')
REPEATED_FLAGS = ('--enable', '--disable')


def add_exec_flags(parser):
    group = parser.add_argument_group('Codex exec options')
    for flag in BOOLEAN_FLAGS:
        group.add_argument(flag, action='store_true', help='Forward this option to Codex exec.')
    for flag in VALUE_FLAGS:
        group.add_argument(flag, help='Forward this value to Codex exec.')
    for flag in REPEATED_FLAGS:
        group.add_argument(flag, action='append', default=[], help='Repeatable native Codex feature switch.')
    safety = group.add_mutually_exclusive_group()
    safety.add_argument('-s', '--sandbox', choices=('read-only', 'workspace-write', 'danger-full-access'), help='Native sandbox selection; default: workspace-write.')
    safety.add_argument('--approve-for-me', action='store_true', help='Use native automatic approval review.')
    safety.add_argument('--dangerously-bypass-approvals-and-sandbox', action='store_true', help='Native bypass option; requires an externally isolated environment.')
    group.add_argument('-a', '--ask-for-approval', choices=('on-request', 'never'), help='Native global approval policy.')
    group.add_argument('--color', choices=('always', 'never', 'auto'), default='never', help='Native output color policy.')
    group.add_argument('--output-schema', metavar='FILE', help='Input JSON schema, resolved from the calling directory.')
    group.add_argument('--json', action='store_true', help='Stream native JSONL events, without duplicate final text.')
    group.add_argument('-o', '--output-last-message', metavar='FILE', help='Keep the final response at this path inside outputs/.')
    group.add_argument('--add-dir', action='append', default=[], metavar='DIR', help='Recognized but conflicts with the outputs-only workspace.')
    group.add_argument('--worktree', action='store_true', help='Recognized but conflicts with the outputs-only workspace.')
    group.add_argument('-V', '--version', action='store_true', help='Show the installed Codex version without starting a task.')


def collect_exec_args(args):
    result = []
    for flag in BOOLEAN_FLAGS:
        if getattr(args, flag[2:].replace('-', '_')):
            result.append(flag)
    for flag in VALUE_FLAGS:
        value = getattr(args, flag[2:].replace('-', '_'))
        if value is not None:
            result.extend([flag, value])
    for flag in REPEATED_FLAGS:
        for value in getattr(args, flag[2:].replace('-', '_')):
            result.extend([flag, value])
    for flag in ('--approve-for-me', '--dangerously-bypass-approvals-and-sandbox'):
        if getattr(args, flag[2:].replace('-', '_')):
            result.append(flag)
    if args.output_schema:
        result.extend(['--output-schema', args.output_schema])
    return tuple(result)
