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
