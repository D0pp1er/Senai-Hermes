import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai.skills import Check, Registry, SkillError
from senai.skills.cli import main


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class GitHubImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        self.registry = Registry(self.project / "outputs/skills")
        self.commit = "a" * 40
        self.tree_sha = "b" * 40
        self.files = {"SKILL.md": b"---\nname: example\ndescription: Example public skill\nversion: 1\n---\nCheck output.\n", "references/info.txt": b"Reference data"}
        self.entries = [dict(path="skills/example", type="tree", mode="040000", sha="c" * 40)]
        for name, data in self.files.items():
            self.entries.append(dict(path="skills/example/" + name, type="blob", mode="100644", sha=blob(data), size=len(data)))
        self.calls = []
        self.truncated = False

    def fetch(self, url, *, max_bytes):
        self.calls.append(url)
        if "/git/commits/" in url:
            return json.dumps(dict(sha=self.commit, tree=dict(sha=self.tree_sha))).encode()
        if "/git/trees/" in url:
            return json.dumps(dict(sha=self.tree_sha, tree=self.entries, truncated=self.truncated)).encode()
        prefix = "https://raw.githubusercontent.com/example/repo/" + self.commit + "/skills/example/"
        if url.startswith(prefix):
            return self.files[url[len(prefix):]]
        self.fail("Unexpected URL: " + url)

    def acquire(self, **overrides):
        args = dict(commit=self.commit, path="skills/example", fetch=self.fetch)
        args.update(overrides)
        return self.registry.import_github("example/repo", **args)

    def test_pinned_import_retains_bytes_source_hash_and_restart(self):
        skill = self.acquire()
        self.assertEqual(skill.source, "https://github.com/example/repo/tree/" + self.commit + "/skills/example")
        self.assertEqual((skill.path.parent / "references/info.txt").read_bytes(), self.files["references/info.txt"])
        self.assertEqual(Registry(self.registry.root).select(["example"]), [skill])
        self.assertEqual(len(skill.digest), 64)
        self.assertEqual(len(self.calls), 4)

    def test_invalid_repo_commit_and_path_never_fetch(self):
        for args in (dict(commit="main"), dict(commit="a" * 7), dict(path="../outside"), dict(path="/absolute"), dict(path="skills/../example"), dict(path="skills\\example"), dict(path="C:/escape")):
            with self.subTest(args=args):
                with self.assertRaises(SkillError):
                    self.acquire(**args)
        with self.assertRaises(SkillError):
            self.registry.import_github("https://user:secret@github.com/a/b", commit=self.commit, path="skills/example", fetch=self.fetch)
        self.assertEqual(self.calls, [])

    def test_truncated_tree_and_wrong_commit_identity_are_rejected(self):
        self.truncated = True
        with self.assertRaises(SkillError):
            self.acquire()
        self.assertEqual(self.registry.list(), [])
        self.truncated = False
        def wrong(url, *, max_bytes):
            if "/git/commits/" in url:
                return json.dumps(dict(sha="d" * 40, tree=dict(sha=self.tree_sha))).encode()
            return self.fetch(url, max_bytes=max_bytes)
        with self.assertRaises(SkillError):
            self.acquire(fetch=wrong)

    def test_symlink_submodule_traversal_and_duplicate_entries_are_rejected(self):
        original = list(self.entries)
        bad_entries = [dict(path="skills/example/link", type="blob", mode="120000", sha="c" * 40, size=4), dict(path="skills/example/module", type="commit", mode="160000", sha="c" * 40), dict(path="skills/example/../../outside", type="blob", mode="100644", sha="c" * 40, size=4), dict(original[1])]
        for entry in bad_entries:
            with self.subTest(entry=entry):
                self.entries = original + [entry]
                with self.assertRaises(SkillError):
                    self.acquire()
                self.assertEqual(self.registry.list(), [])

    def test_corrupt_blob_or_network_failure_does_not_activate_partial_package(self):
        before = set(self.registry.root.iterdir())
        self.files["references/info.txt"] = b"Corrupted bytes"
        with self.assertRaises(SkillError):
            self.acquire()
        self.assertEqual(self.registry.list(), [])
        self.assertEqual(set(self.registry.root.iterdir()), before)
        def broken(url, *, max_bytes):
            raise RuntimeError("private transport details")
        with self.assertRaises(SkillError) as error:
            self.acquire(fetch=broken)
        self.assertNotIn("private transport details", str(error.exception))

    def test_unsupported_metadata_does_not_activate(self):
        self.files["SKILL.md"] = b"---\nname: example\ndescription: Test\nunsupported: shell\n---\nInstructions\n"
        self.entries[1].update(sha=blob(self.files["SKILL.md"]), size=len(self.files["SKILL.md"]))
        with self.assertRaises(SkillError):
            self.acquire()
        self.assertEqual(self.registry.list(), [])

    def test_limits_are_checked_before_downloading_selected_blobs(self):
        for update in (dict(size=1024 * 1024 + 1), dict(size=-1)):
            self.entries[1].update(update)
            with self.assertRaises(SkillError):
                self.acquire()
            self.assertFalse(any("raw.githubusercontent.com" in url for url in self.calls))
        self.assertEqual(self.registry.list(), [])

    def test_conflicting_import_does_not_overwrite_local_revision_or_original(self):
        original = self.acquire()
        outcome = self.registry.record_outcome("example", digest=original.digest, request="Check", result="Wrong", checks=(Check("case", False, "Observed failure"),))
        revision = self.registry.propose_revision("example", document=self.files["SKILL.md"].decode().replace("version: 1", "version: 2").replace("Check output.", "Check output and boundaries."), outcome_ids=(outcome.id,), reason="Fix observed failure")
        self.registry.validate_revision(revision.id, validator=lambda *args: (Check("case", True, "Observed pass"),))
        active = self.registry.activate_revision(revision.id)
        with self.assertRaises(SkillError):
            self.acquire()
        self.assertEqual(self.registry.list(), [active])
        self.assertEqual(self.registry.versions("example"), [original, active])

    def test_cli_routes_pinned_public_import(self):
        out, err = io.StringIO(), io.StringIO()
        # Exercise CLI + actual registry importer, substituting only HTTP bytes.
        with patch("senai.skills.sources.fetch_public", side_effect=self.fetch):
            code = main(["--project", str(self.project), "import-github", "example/repo", "--commit", self.commit, "--path", "skills/example"], stdout=out, stderr=err)
        self.assertEqual(code, 0, err.getvalue())
        self.assertEqual(json.loads(out.getvalue())["source"], "https://github.com/example/repo/tree/" + self.commit + "/skills/example")

    def test_package_ancestor_symlink_is_rejected(self):
        self.entries.insert(0, dict(path="skills", type="blob", mode="120000", sha="c" * 40, size=6))
        with self.assertRaises(SkillError):
            self.acquire()
        self.assertEqual(self.registry.list(), [])

    def test_root_directory_package_is_supported(self):
        self.entries = [dict(entry, path=entry["path"].removeprefix("skills/example/")) for entry in self.entries[1:]]
        def root_fetch(url, *, max_bytes):
            prefix = "https://raw.githubusercontent.com/example/repo/" + self.commit + "/"
            if url.startswith(prefix):
                return self.files[url[len(prefix):]]
            return self.fetch(url, max_bytes=max_bytes)
        skill = self.acquire(path=".", fetch=root_fetch)
        self.assertEqual(skill.source, "https://github.com/example/repo/tree/" + self.commit)

    def test_network_host_credentials_redirects_and_response_limits_are_enforced(self):
        from senai.skills.sources import fetch_public, _NoRedirect
        with patch("urllib.request.build_opener") as opener:
            for url in ("http://api.github.com/x", "https://user:secret@api.github.com/x", "https://evil.example/x", "https://api.github.com:443/x"):
                with self.assertRaises(SkillError):
                    fetch_public(url, max_bytes=1)
            opener.assert_not_called()
        with self.assertRaises(SkillError):
            _NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://evil.example/")
        with patch("urllib.request.build_opener") as opener:
            opener.return_value.open.return_value.__enter__.return_value.read.return_value = b"too long"
            with self.assertRaises(SkillError):
                fetch_public("https://api.github.com/example", max_bytes=1)

    def test_aggregate_size_and_file_count_limits_precede_blob_requests(self):
        initial = list(self.entries)
        for count, size in ((8, 1024 * 1024), (256, 0)):
            self.entries = initial + [dict(path="skills/example/file-" + str(index), type="blob", mode="100644", sha="c" * 40, size=size) for index in range(count)]
            with self.assertRaises(SkillError):
                self.acquire()
            self.assertFalse(any("raw.githubusercontent.com" in url for url in self.calls))
        self.assertEqual(self.registry.list(), [])
