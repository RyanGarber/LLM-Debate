from typing import Sequence, Type

from pydantic import BaseModel

from data.message import Message, Model, Decision
from data.debate import Debate


def build_system_prompt(debate: Debate, model: Model, role: str) -> str:
    if role == "proponent":
        system_prompt = f"You are {model.name}. You are debating {debate.opponent}.\n"
        system_prompt += f"Your position is: {debate.topic}\n"
    elif role == "opponent":
        system_prompt = f"You are {model.name}. You are debating {debate.proponent}.\n"
        system_prompt += f"You disagree with: {debate.topic}\n"
    elif role == "moderator":
        system_prompt = f"You are {model.name}. You are moderating a debate between a proponent ({debate.proponent}) and opponent ({debate.opponent}).\n"
        system_prompt += f"The topic of the debate is: {debate.topic}\n"
    else:
        raise ValueError(f"Invalid role: {role}")

    if role != "moderator":
        system_prompt += f"Do not explain that you ({model.name}) are writing {model.name}'s argument, just argue it.\n"
        system_prompt += f"Be concise and persuasive. Keep responses under 250 words.\n"

    print("[Prompt] System:", system_prompt)

    return system_prompt


def build_output_type(message: Message) -> Type[BaseModel] | Type[str]:
    output_type = str

    if message.role == "moderator":
        output_type = Decision

    print("[Prompt] Output:", output_type)

    return output_type


def build_prompt(
    debate: Debate, model: Model, message: Message
) -> tuple[str, str | Sequence[str], Type[BaseModel] | Type[str]]:
    user_prompt = ""
    system_prompt = build_system_prompt(debate, model, message.role)
    output_type = build_output_type(message)

    if not model.supports_system_prompt:
        user_prompt += f"CRITICAL INSTRUCTIONS:\n{system_prompt}\n\n"
        system_prompt = ()

    if len(debate.messages) > 1:
        user_prompt += f"---\nDEBATE HISTORY:\n\n"
        for m in debate.messages:
            if m.response_content is not None:
                user_prompt += f"\n\n[{m.model}]\n{m.response_content}"
        user_prompt += "\n\n---\n\n"

    if message.role == "moderator":
        user_prompt += f"As the moderator, it's your job to keep the debate focused and moving forward.\n"
        user_prompt += f"Provide follow-up questions that force the participants to confront the core disagreement of the debate.\n"
        user_prompt += f"If an argument is weak or tangential, use your follow-up question to steer the debate back on track.\n"
    else:
        follow_up = message.get_follow_up(debate.messages)
        if follow_up is not None:
            user_prompt += f"The moderator has asked you to respond to: {follow_up}\n"
            user_prompt += f"Make sure to address this in your argument.\n"
        else:
            user_prompt += f"Your turn. Make {model.name}'s next argument.\n"

    print("[Prompt] User:", user_prompt)

    return user_prompt, system_prompt, output_type
