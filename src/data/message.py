from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai.models import Model as PydanticModel


@dataclass
class Model:
    name: str
    provider: PydanticModel
    supports_system_prompt: bool


@dataclass
class Message:
    role: str
    model: str
    thinking_content: str | None = None
    response_content: str | None = None
    decision: Decision | None = None
    generating: bool = False

    def is_pending(self) -> bool:
        return (
            self.response_content is None
            and self.decision is None
            and not self.generating
        )

    def get_follow_up(self, messages: list[Message]):
        i = messages.index(self)
        while i > 0:
            if messages[i].role == "moderator":
                if messages[i].decision is not None:
                    if self.role == "proponent":
                        return messages[i].decision.proponent_follow_up
                    elif self.role == "opponent":
                        return messages[i].decision.opponent_follow_up
                break
            i -= 1
        return None

    def regenerate(self):
        self.thinking_content = None
        self.response_content = None
        self.decision = None
        self.generating = False


class Decision(BaseModel):
    agreements: list[str] = Field(
        description="A list of points the participants agree on."
    )
    core_disagreement: str = Field(description="The core disagreement of the debate.")
    winner_is_proponent: bool = Field(
        description="Whether the proponent is winning the debate."
    )
    winner_is_opponent: bool = Field(
        description="Whether the opponent is winning the debate."
    )
    winner_explanation: str = Field(
        description="An explanation of why the current winner is winning or losing the debate."
    )
    proponent_follow_up: str = Field(
        description="A follow-up question for the proponent."
    )
    opponent_follow_up: str = Field(
        description="A follow-up question for the opponent."
    )


@dataclass
class MessageDelta:
    thinking: str | None = None
    response: str | None = None
    output: str | None = None
