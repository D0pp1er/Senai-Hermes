"""Validate project paths and prepare the output workspace."""

from pathlib import Path


def prepare_workspace(project_path):
    project = Path(project_path).expanduser().resolve()
    if not project.is_dir():
        raise ValueError('Project must be an existing directory.')
    workspace = project / 'outputs'
    if workspace.is_symlink():
        raise ValueError('outputs must be a real directory, not a symlink.')
    workspace.mkdir(exist_ok=True)
    return workspace


def resolve_output_path(workspace, value):
    """Resolve an explicit generated output path inside the selected workspace."""
    workspace = Path(workspace).resolve()
    path = Path(value).expanduser()
    path = (workspace / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_relative_to(workspace) or path == workspace:
        raise ValueError('Output file must stay inside outputs/.')
    if path.is_dir():
        raise ValueError('Output path must name a file inside outputs/, not a directory.')
    return path
