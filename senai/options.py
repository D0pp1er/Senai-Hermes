"""Explicit Codex execution options; values never pass through a shell."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CodexOptions:
    model: str | None = None
    profile: str | None = None
    config: tuple[str, ...] = ()
    images: tuple[str, ...] = ()
    search: bool = False
    resume: str | None = None
    last: bool = False
    skip_git_repo_check: bool = False
    extra_args: tuple[str, ...] = ()
    sandbox: str | None = 'workspace-write'
    color: str = 'never'
    approval: str | None = None
    output_last_message: str | None = None
    json: bool = False

    def to_args(self):
        args = []
        if self.model:
            args.extend(['--model', self.model])
        if self.profile:
            args.extend(['--profile', self.profile])
        for value in self.config:
            args.extend(['--config', value])
        for image in self.images:
            args.extend(['--image', image])
        if self.search:
            args.extend(['--config', 'web_search="live"'])
        if self.skip_git_repo_check:
            args.append('--skip-git-repo-check')
        args.extend(self.extra_args)
        return args

    def session_args(self):
        if self.resume is not None and self.last:
            raise ValueError('Choose --resume or --last, not both.')
        if self.resume is not None:
            if not self.resume.strip() or self.resume.startswith('-'):
                raise ValueError('Session must be a nonempty id or name, not an option.')
            return ['resume', self.resume]
        return ['resume', '--last'] if self.last else []
