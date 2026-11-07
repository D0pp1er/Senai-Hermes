"""Explicit Codex execution options; values never pass through a shell."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CodexOptions:
    model: str | None = None
    profile: str | None = None
    config: tuple[str, ...] = ()

    def to_args(self):
        args = []
        if self.model:
            args.extend(['--model', self.model])
        if self.profile:
            args.extend(['--profile', self.profile])
        for value in self.config:
            args.extend(['--config', value])
        return args
