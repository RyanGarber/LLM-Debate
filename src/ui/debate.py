import asyncio

import streamlit as st

from logic.message import process_message
from data.message import Model
from data.debate import Debate


def render_debate(debate: Debate, models: list[Model]):
    with st.chat_message(name="user", avatar="⬛"):
        st.markdown(f"###### {debate.topic}")

    for i, message in enumerate(debate.messages):
        name = message.role
        avatar = None
        if message.role == "proponent":
            avatar = "🟩"
        elif message.role == "opponent":
            avatar = "🟥"
        elif message.role == "moderator":
            avatar = "⬜"
            name = "user"
        with st.chat_message(name=name, avatar=avatar):
            st.markdown(f"###### {message.role.capitalize()} `{message.model}`")

            follow_up = message.get_follow_up(debate.messages)
            if follow_up is not None:
                st.markdown(f"\n> **Moderator:** {follow_up}")

            if message.is_pending():

                async def _run():
                    status = st.status("Preparing...")

                    thinking = status.empty()
                    thinking_content = ""
                    response = st.empty()
                    response_content = ""

                    stream = process_message(debate, models, message)
                    async for delta in stream:
                        if delta.thinking is not None:
                            status.update(label="Thinking...")
                            thinking_content += delta.thinking
                            thinking.markdown(thinking_content)

                        if delta.response is not None:
                            status.update(label="Responding...")
                            response_content += delta.response
                            response.markdown(response_content)

                        if delta.output is not None:
                            status.update(label="Deciding...")
                            response_content += delta.output
                            response.code(response_content)

                    st.rerun()

                asyncio.run(_run())
            else:
                col1, col2 = st.columns((0.925, 0.075))
                with col1.status(label="Done", state="complete"):
                    st.markdown(message.thinking_content)
                if col2.button(label="↺", type="tertiary", key=f"regen_{i}"):
                    message.regenerate()
                    st.rerun()

                if message.decision is not None:
                    st.markdown(f"""
###### Agreements
{"*None*" if len(message.decision.agreements) == 0 else f"- {"\n- ".join(message.decision.agreements)}"}

###### Disagreement
{message.decision.core_disagreement}

###### Takeaway
*{"No clear winner yet." if message.decision.winner_is_proponent == message.decision.winner_is_opponent else f"{f"🟩 `{debate.proponent}`" if message.decision.winner_is_proponent else f"🟥 `{debate.opponent}`"} is winning the argument."}*

{message.decision.winner_explanation}
""")
                else:
                    st.markdown(message.response_content)
