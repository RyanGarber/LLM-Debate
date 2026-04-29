from typing import AsyncGenerator

from pydantic_ai import (
    Agent,
    AgentRunResultEvent,
    PartStartEvent,
    PartDeltaEvent,
    TextPartDelta,
    TextPart,
    ThinkingPart,
    ThinkingPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
    FinalResultEvent,
    PartEndEvent,
)

from data.message import Message, Model, MessageDelta, Decision
from data.debate import Debate
from logic.prompt import build_prompt


def create_next_message(state: Debate) -> Message:
    print("[Message] Creating next message...")

    last_message = state.messages[-1] if state.messages else None

    if last_message is None or last_message.role == "moderator":
        return Message(
            role="proponent",
            model=state.proponent,
        )
    elif last_message.role == "proponent":
        return Message(
            role="opponent",
            model=state.opponent,
        )
    elif last_message.role == "opponent":
        return Message(
            role="moderator",
            model=state.moderator,
        )

    raise ValueError("Invalid last message role")


async def process_message(
    debate: Debate, models: list[Model], message: Message
) -> AsyncGenerator[MessageDelta, None]:
    print(f"[Message] Processing message...")
    message.generating = True

    model = [m for m in models if m.name == message.model][0]
    user_prompt, system_prompt, output_type = build_prompt(debate, model, message)

    output_id = -1

    agent = Agent(model=model.provider, system_prompt=system_prompt)
    async for event in agent.run_stream_events(
        user_prompt=user_prompt, output_type=output_type
    ):
        if (
            isinstance(event, PartStartEvent) and isinstance(event.part, ThinkingPart)
        ) or (
            isinstance(event, PartDeltaEvent)
            and isinstance(event.delta, ThinkingPartDelta)
        ):
            yield MessageDelta(
                thinking=(
                    event.part.content
                    if isinstance(event, PartStartEvent)
                    else event.delta.content_delta
                )
            )

        if (isinstance(event, PartStartEvent) and isinstance(event.part, TextPart)) or (
            isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta)
        ):
            yield MessageDelta(
                response=(
                    event.part.content
                    if isinstance(event, PartStartEvent)
                    else event.delta.content_delta
                )
            )

        if isinstance(event, FinalResultEvent):
            output_id = event.tool_call_id

        if (
            isinstance(event, PartStartEvent) and isinstance(event.part, ToolCallPart)
        ) or (
            isinstance(event, PartDeltaEvent)
            and isinstance(event.delta, ToolCallPartDelta)
        ):
            id = (
                event.part.tool_call_id
                if isinstance(event, PartStartEvent)
                else event.delta.tool_call_id
            )
            if id == output_id:
                yield MessageDelta(
                    output=(
                        event.part.args
                        if isinstance(event, PartStartEvent)
                        else event.delta.args_delta
                    )
                )

        if isinstance(event, PartEndEvent) and isinstance(event.part, ThinkingPart):
            message.thinking_content = event.part.content

        if isinstance(event, AgentRunResultEvent):
            if isinstance(event.result.output, Decision):
                print("[Message] Finished with decision output")
                message.decision = event.result.output
            else:
                print("[Message] Finished with text output")
                message.response_content = event.result.output

        print("[Message] Event:", event)

    message.generating = False
