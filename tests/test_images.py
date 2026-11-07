import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai import cli
from senai.options import CodexOptions


class ImageTests(unittest.TestCase):
    def test_repeated_images_are_separate_arguments(self):
        options = CodexOptions(images=('/tmp/design one.png', '/tmp/design two.png'))
        self.assertEqual(options.to_args(), ['--image', '/tmp/design one.png', '--image', '/tmp/design two.png'])

    def test_cli_resolves_attachments_before_switching_workspace(self):
        with tempfile.TemporaryDirectory() as project:
            image = Path(project) / 'design one.png'
            image.write_bytes(b'image fixture')
            with patch('senai.cli.run_codex', return_value='Done') as run:
                self.assertEqual(cli.main(['--project', project, '-i', str(image), 'Build this design'], io.StringIO(), io.StringIO()), 0)
                self.assertEqual(run.call_args.kwargs['options'].images, (str(image.resolve()),))

    def test_missing_attachment_fails_before_execution(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.cli.run_codex') as run:
            err = io.StringIO()
            self.assertEqual(cli.main(['--project', project, '-i', str(Path(project) / 'missing.png'), 'Build this'], io.StringIO(), err), 2)
            run.assert_not_called()
            self.assertIn('Image', err.getvalue())
            self.assertFalse((Path(project) / 'outputs').exists())
