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
        return args

    def session_args(self):
        if self.resume is not None and self.last:
            raise ValueError('Choose --resume or --last, not both.')
        if self.resume is not None:
            if not self.resume.strip() or self.resume.startswith('-'):
                raise ValueError('Session must be a nonempty id or name, not an option.')
            return ['resume', self.resume]
        return ['resume', '--last'] if self.last else []
