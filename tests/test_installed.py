"""Exercise the installed console script and a real child process, offline."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


COMMAND = shutil.which('senai') or (str(Path.home() / '.local/bin/senai') if (Path.home() / '.local/bin/senai').is_file() else None)


@unittest.skipUnless(COMMAND, 'Install the package before console integration tests.')
class InstalledCommandTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        binaries = self.project / 'bin'
        binaries.mkdir()
        executable = binaries / 'codex'
        executable.write_text("""#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
args = sys.argv[1:]
prompt = sys.stdin.read() if args[-1:] == ['-'] else ''
Path('transport.json').write_text(json.dumps({'args': args, 'cwd': str(Path.cwd()), 'prompt': prompt}))
if os.environ.get('SENAI_TEST_FAIL'):
    print('fixture failure', file=sys.stderr)
    raise SystemExit(23)
if '--output-last-message' in args:
    Path(args[args.index('--output-last-message') + 1]).write_text('Created code')
else:
    print('Native output')
""")
        executable.chmod(0o755)
        self.environment = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ['PATH'])
        self.command = COMMAND

    def invoke(self, arguments, **environment):
        return subprocess.run([self.command, *arguments], cwd=self.project, env=dict(self.environment, **environment), text=True, capture_output=True, timeout=15)

    def test_write_command_uses_outputs_and_preserves_literal_prompt(self):
        result = self.invoke(['--search', '-m', 'fixture-model', '--skill', 'fixture-skill', 'Create a file; $literal'])
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.project / 'outputs'
        self.assertTrue((output / 'transport.json').exists(), 'Child process must start inside outputs/')
        trace = json.loads((output / 'transport.json').read_text())
        self.assertEqual(result.stdout, 'Created code\n')
        self.assertIn('$fixture-skill', trace['prompt'])
        self.assertIn('Create a file; $literal', trace['prompt'])
        self.assertIn('fixture-model', trace['args'])
        self.assertEqual(trace['cwd'], str(output))
        self.assertFalse(list(output.glob('.senai-*')), 'Temporary final responses should be cleaned')

    def test_native_streams_and_failure_status_cross_process_boundary(self):
        result = self.invoke(['codex', '--', 'features', 'list'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'Native output\n')
        trace = json.loads((self.project / 'outputs/transport.json').read_text())
        self.assertEqual(trace['args'][-2:], ['features', 'list'])
        failure = self.invoke(['codex', '--', 'features', 'list'], SENAI_TEST_FAIL='1')
        self.assertEqual(failure.returncode, 23)
        self.assertIn('fixture failure', failure.stderr)
