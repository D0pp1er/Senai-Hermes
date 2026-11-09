"""Pinned public GitHub acquisition; no credentials, checkout, archive or code execution."""
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from .errors import SkillError


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SkillError("Public skill fetch redirects are unsupported")


def fetch_public(url, *, max_bytes):
    """Unauthenticated bounded HTTPS GET to fixed GitHub hosts, 20s socket timeout."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {"api.github.com", "raw.githubusercontent.com"} or parsed.username or parsed.password or parsed.port or parsed.fragment:
        raise SkillError("Unsupported public skill URL")
    request = urllib.request.Request(url, headers={"User-Agent": "senai-skills/0.1", "Accept": "application/vnd.github+json" if parsed.hostname == "api.github.com" else "application/octet-stream", "X-GitHub-Api-Version": "2022-11-28"})
    # Do not inherit authenticated proxy settings or environment GitHub tokens.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(request, timeout=20) as response:
            data = response.read(max_bytes + 1)
    except Exception as exc:
        raise SkillError("Public GitHub fetch failed; check availability or rate limits") from exc
    if len(data) > max_bytes:
        raise SkillError("Public skill response exceeded its size limit")
    return data


def _path(value, *, root_allowed=False):
    if root_allowed and value == ".":
        return ""
    if not isinstance(value, str) or not value or len(value) > 1024 or "\\" in value or ":" in value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise SkillError("Unsafe repository package path")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise SkillError("Repository paths must be relative and cannot escape")
    return value


def import_github(registry, repository, *, commit, path, fetch=None):
    """Fetch a whole selected package subtree pinned to a full SHA-1 commit.

    fetch(url, *, max_bytes) -> bytes may inject deterministic transport. This is
    syntax/content integrity validation, not a safety scanner or runtime approval.
    """
    if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}", repository) or repository.split("/")[1] in {".", ".."}:
        raise SkillError("Repository must be a public GitHub owner/repo identifier")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise SkillError("Supply an exact 40-character lowercase commit SHA; branches/tags are unsupported")
    package = _path(path, root_allowed=True)
    transport = fetch_public if fetch is None else fetch

    def read(url, limit):
        try:
            data = transport(url, max_bytes=limit)
        except Exception as exc:
            raise SkillError("Public GitHub fetch failed; no skill was activated") from exc
        if not isinstance(data, bytes) or len(data) > limit:
            raise SkillError("Public response is not bounded bytes")
        return data

    def object_at(url, limit):
        try:
            data = json.loads(read(url, limit))
        except (ValueError, RecursionError) as exc:
            raise SkillError("Invalid GitHub metadata response") from exc
        if not isinstance(data, dict):
            raise SkillError("GitHub metadata must be an object")
        return data

    api = "https://api.github.com/repos/" + repository
    commit_data = object_at(api + "/git/commits/" + commit, 128 * 1024)
    tree_id = commit_data.get("tree", {}).get("sha") if isinstance(commit_data.get("tree"), dict) else None
    if commit_data.get("sha") != commit or not isinstance(tree_id, str) or not re.fullmatch(r"[0-9a-f]{40}", tree_id):
        raise SkillError("Commit identity did not match requested immutable revision")
    tree = object_at(api + "/git/trees/" + tree_id + "?recursive=1", 4 * 1024 * 1024)
    if tree.get("sha") != tree_id or tree.get("truncated") is not False or not isinstance(tree.get("tree"), list) or len(tree["tree"]) > 50000:
        raise SkillError("Incomplete, excessive or wrong Git tree")
    prefix = package + "/" if package else ""
    ancestors = {"/".join(package.split("/")[:index]) for index in range(1, len(package.split("/")) + 1)} if package else set()
    found_root = not package
    selected = {}
    paths = set()
    total = 0
    for entry in tree["tree"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise SkillError("Invalid Git tree entry")
        raw_path = entry["path"]
        if raw_path in ancestors:
            if entry.get("type") != "tree" or entry.get("mode") != "040000":
                raise SkillError("Package ancestors cannot be symlinks/submodules/files")
            if raw_path == package:
                found_root = True
        if not raw_path.startswith(prefix) or raw_path == package:
            continue
        _path(raw_path)
        relative = _path(raw_path[len(prefix):])
        if relative in paths:
            raise SkillError("Duplicate package entry")
        paths.add(relative)
        if entry.get("type") == "tree" and entry.get("mode") == "040000":
            continue
        if entry.get("type") != "blob" or entry.get("mode") not in {"100644", "100755"}:
            raise SkillError("Package symlinks, submodules and nonregular files unsupported")
        size = entry.get("size")
        sha = entry.get("sha")
        if type(size) is not int or size < 0 or size > 1024 * 1024 or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise SkillError("Invalid package file size or Git blob identity")
        total += size
        if total > 8 * 1024 * 1024 or len(selected) >= 256:
            raise SkillError("Package exceeds 256 files or 8 MiB")
        selected[relative] = (raw_path, size, sha)
    if not found_root or "SKILL.md" not in selected:
        raise SkillError("Selected directory has no SKILL.md")
    files = {}
    for relative, (raw_path, size, sha) in sorted(selected.items()):
        url = "https://raw.githubusercontent.com/" + repository + "/" + commit + "/" + urllib.parse.quote(raw_path, safe="/")
        data = read(url, size)
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if len(data) != size or actual != sha:
            raise SkillError("Downloaded bytes did not match the pinned Git blob")
        files[relative] = data
    source = "https://github.com/" + repository + "/tree/" + commit + ("/" + urllib.parse.quote(package, safe="/") if package else "")
    return registry._import_files(files, source, origin={"kind": "imported", "source_kind": "github"})
