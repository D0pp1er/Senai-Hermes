"""Bounded SKILL.md YAML reader: no constructors, aliases, anchors or custom tags."""
import re

from .errors import SkillError


def _yaml_mapping(header):
    try:
        import yaml
    except ImportError as exc:
        raise SkillError("Install this feature's requirements-skills.txt into the project .venv") from exc
    try:
        depth = 0
        for count, event in enumerate(yaml.parse(header, Loader=yaml.BaseLoader), 1):
            if count > 1024 or isinstance(event, yaml.AliasEvent) or getattr(event, "anchor", None) or getattr(event, "tag", None):
                raise SkillError("Metadata aliases, anchors, tags or excessive nodes are unsupported")
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                depth += 1
                if depth > 8:
                    raise SkillError("Metadata nesting exceeds eight levels")
            elif isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                depth -= 1
        node = yaml.compose(header, Loader=yaml.BaseLoader)
    except yaml.YAMLError as exc:
        raise SkillError("Malformed YAML metadata") from exc

    def convert(node):
        if isinstance(node, yaml.ScalarNode):
            if node.style is None and node.value in {"", "null", "Null", "NULL", "~"}:
                return None
            return node.value
        if isinstance(node, yaml.SequenceNode):
            return [convert(value) for value in node.value]
        if isinstance(node, yaml.MappingNode):
            result = {}
            for key_node, value_node in node.value:
                if not isinstance(key_node, yaml.ScalarNode):
                    raise SkillError("Metadata keys must be scalar strings")
                key = key_node.value
                if not key or key == "<<" or key in result:
                    raise SkillError("Empty, duplicate or merge metadata key")
                result[key] = convert(value_node)
            return result
        raise SkillError("Metadata requires a YAML mapping")

    value = convert(node)
    if not isinstance(value, dict):
        raise SkillError("Metadata header must be a mapping")
    return value


def _text(value, label, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise SkillError("Invalid skill " + label)


def _inert(value):
    if isinstance(value, str):
        return
    if isinstance(value, list):
        for item in value:
            _inert(item)
        return
    if isinstance(value, dict):
        for item in value.values():
            _inert(item)
        return
    raise SkillError("Metadata values must be strings, lists or mappings")


def parse_document(data):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SkillError("SKILL.md must be UTF-8") from exc
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise SkillError("Missing metadata header")
    for index, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            break
    else:
        raise SkillError("Unterminated metadata header")
    header = "".join(lines[1:index])
    if len(header.encode("utf-8")) > 16 * 1024:
        raise SkillError("Metadata header exceeds 16 KiB")
    metadata = _yaml_mapping(header)
    allowed = {"name", "description", "version", "license", "compatibility", "metadata", "allowed-tools"}
    if set(metadata) - allowed:
        raise SkillError("Unsupported skill metadata field")
    name = metadata.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
        raise SkillError("Invalid skill name")
    _text(metadata.get("description"), "description", 1024)
    for key, maximum in (("license", 2048), ("compatibility", 500), ("allowed-tools", 2048)):
        if key in metadata:
            _text(metadata[key], key, maximum)
    extra = metadata.get("metadata", {})
    if not isinstance(extra, dict):
        raise SkillError("metadata must be a mapping")
    _inert(extra)
    nested_version = extra.get("version")
    version = metadata.get("version", nested_version if nested_version is not None else "1")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", version):
        raise SkillError("Invalid version")
    if nested_version is not None and nested_version != version:
        raise SkillError("Conflicting version fields")
    metadata["version"] = version
    instructions = "".join(lines[index + 1:])
    if not instructions.strip():
        raise SkillError("Instructions required")
    return metadata, instructions


def policy_metadata(metadata):
    """Optional declarations preserved by instruction-only revisions."""
    result = {key: value for key, value in metadata.items() if key not in {"name", "description", "version"}}
    if "metadata" in result:
        result["metadata"] = {key: value for key, value in result["metadata"].items() if key != "version"}
    return result
