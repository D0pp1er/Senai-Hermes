"""Minimal transport contract. Identity and authorization are outside model prompts."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class IncomingRequest:
    platform: str
    account: str
    project: str
    event_id: str
    user_id: str
    delivery_target: str
    text: str
    session_name: str

    @property
    def request_id(self) -> tuple[str, str, str, str]:
        return self.platform, self.account, self.project, self.event_id

    @property
    def session_scope(self) -> tuple[str, str, str, str]:
        return self.platform, self.account, self.project, self.session_name


@runtime_checkable
class TransportAdapter(Protocol):
    def normalize(self, event: object) -> IncomingRequest | None: ...
    def is_authorized(self, user_id: str) -> bool: ...
    def handle(self, event: object) -> list[tuple[int | str, str]]: ...
    def delivery_parts(self, text: str) -> list[str]: ...
    def send_text(self, target: str, text: str) -> None: ...
