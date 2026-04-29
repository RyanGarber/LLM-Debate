from dataclasses import dataclass, field

from data.message import Message


@dataclass
class Debate:
    proponent: str = ""
    opponent: str = ""
    moderator: str = ""
    topic: str = ""
    mode: str = ""

    messages: list[Message] = field(default_factory=list)
    active: bool = False

    def to_saved(self) -> dict:
        return {
            "proponent": self.proponent,
            "opponent": self.opponent,
            "moderator": self.moderator,
            "topic": self.topic,
            "mode": self.mode,
        }

    @classmethod
    def from_saved(cls, data: dict):
        return cls(
            proponent=data.get("proponent", ""),
            opponent=data.get("opponent", ""),
            moderator=data.get("moderator", ""),
            topic=data.get("topic", ""),
            mode=data.get("mode", ""),
        )


@dataclass
class DebateValidation:
    proponent: bool
    opponent: bool
    moderator: bool
    topic: bool
    mode: bool

    def __init__(self, debate: Debate):
        self.proponent = bool(debate.proponent)
        self.opponent = bool(debate.opponent)
        self.moderator = bool(debate.moderator)
        self.topic = bool(debate.topic)
        self.mode = bool(debate.mode)

    def all(self):
        return all(
            [
                self.proponent,
                self.opponent,
                self.moderator,
                self.topic,
                self.mode,
            ]
        )
