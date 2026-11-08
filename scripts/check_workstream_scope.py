#!/usr/bin/env python3
"""Audit feature ownership against coordinator policy and optional delivery readiness."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

POLICY = 'projectprogress/parallel/ownership.json'


def git(repo, *arguments):
    result = subprocess.run(['git', *arguments], cwd=repo, capture_output=True)
    if result.returncode:
        raise ValueError('Git check failed: ' + result.stderr.decode(errors='replace').strip())
    return result.stdout


def changed_paths(repo, base):
    ancestor = git(repo, 'merge-base', base, 'HEAD').decode().strip()
    results = [git(repo, 'diff', '--name-only', '--no-renames', '-z', ancestor, 'HEAD'), git(repo, 'diff', '--name-only', '--no-renames', '-z', 'HEAD'), git(repo, 'ls-files', '--others', '--exclude-standard', '-z')]
    return sorted({item.decode() for result in results for item in result.split(b'\0') if item})


def ready_errors(delivery, feature):
    errors = []
    if delivery.get('schema_version') != 1 or delivery.get('feature') != feature:
        errors.append('delivery schema_version/feature does not match the workstream')
    if delivery.get('status') != 'ready':
        errors.append('delivery is draft, not ready')
    for name in ('modules', 'public_api', 'commands'):
        if not isinstance(delivery.get(name), list) or not delivery[name]:
            errors.append(f'{name} must contain the implemented module/API/CLI contract')
    for api in delivery.get('public_api', []):
        if not isinstance(api, dict) or not all(api.get(key) for key in ('name', 'signature', 'purpose')):
            errors.append('each public_api needs name, signature, and purpose')
    executor = delivery.get('executor_contract', {})
    if not isinstance(executor, dict) or not all(executor.get(key) for key in ('interface', 'inputs', 'outputs')):
        errors.append('executor_contract must describe interface, inputs, and outputs')
    verification = delivery.get('verification', {})
    if not isinstance(verification, dict) or verification.get('offline_result') != 'passed' or not verification.get('offline_commands') or not verification.get('tested_commit') or type(verification.get('offline_test_count')) is not int or verification['offline_test_count'] <= 0:
        errors.append('verification needs passing commands, positive count, and tested commit')
    dependencies = delivery.get('dependencies', {})
    if not isinstance(dependencies, dict) or not all(isinstance(dependencies.get(key), list) for key in ('runtime', 'development')):
        errors.append('dependencies must list runtime and development requirements (empty is valid)')
    storage = delivery.get('storage', {})
    if not isinstance(storage, dict) or not storage.get('namespace') or not storage.get('migration_notes') or type(storage.get('schema_version')) is not int or storage['schema_version'] < 1:
        errors.append('storage needs namespace, positive schema version, and migration notes')
    integration = delivery.get('integration', {})
    if not isinstance(integration, dict) or not all(isinstance(integration.get(key), list) for key in ('shared_file_changes', 'sibling_requirements')):
        errors.append('integration must list shared file changes and sibling requirements')
    if not isinstance(delivery.get('limitations'), list):
        errors.append('limitations must be an explicit list')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='.')
    parser.add_argument('--base', default='main')
    parser.add_argument('--feature', required=True)
    parser.add_argument('--ready', action='store_true', help='Also require a complete delivery manifest.')
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    try:
        policy = json.loads(git(repo, 'show', f'{args.base}:{POLICY}'))
        if policy.get('version') != 1 or args.feature not in policy.get('workstreams', {}):
            raise ValueError('Unknown policy version or feature.')
        owner = policy['workstreams'][args.feature]
        branch = git(repo, 'branch', '--show-current').decode().strip()
        if branch != owner['branch']:
            raise ValueError(f'Expected branch {owner["branch"]}, found {branch}.')
        violations = []
        for path in changed_paths(repo, args.base):
            if path in owner.get('files', []) or any(path.startswith(prefix) for prefix in owner['prefixes']):
                continue
            if path in policy.get('coordinator_paths', []):
                current = repo / path
                if current.is_file() and not current.is_symlink() and current.read_bytes() == git(repo, 'show', f'{args.base}:{path}'):
                    continue
            violations.append(path)
        for path in violations:
            print(f'OUT OF SCOPE: {path}')
        errors = []
        delivery_path = repo / 'projectprogress/workstreams' / args.feature / 'delivery.json'
        if args.ready:
            if not delivery_path.is_file():
                errors.append('delivery.json is missing')
            else:
                errors = ready_errors(json.loads(delivery_path.read_text()), args.feature)
            for error in errors:
                print('NOT READY: ' + error)
        if violations or errors:
            return 1
        print(f'PASS: {args.feature} file ownership' + (' and declared delivery readiness.' if args.ready else '.'))
        if not args.ready:
            print('Scope pass is not merge readiness; use --ready after filling delivery.json.')
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'scope guard: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
