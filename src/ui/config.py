import streamlit as st

from data.debate import Debate, DebateValidation
from data.message import Model
from state import State


@st.fragment
def render_config(debate: Debate, models: list[Model]):
    model_names = [m.name for m in models]

    def model_select(label: str, key: str, current_value: str) -> str:
        st.selectbox(
            label,
            key=key,
            options=model_names,
            index=(
                model_names.index(current_value) if current_value in model_names else 0
            ),
        )
        return st.session_state.get(key, "")

    st.text_input("Topic", key="topic_input", value=debate.topic)
    debate.topic = st.session_state.get("topic_input", "")

    model_select("Proponent", "proponent_input", debate.proponent)
    debate.proponent = st.session_state.get("proponent_input", "")

    model_select("Opponent", "opponent_input", debate.opponent)
    debate.opponent = st.session_state.get("opponent_input", "")

    model_select("Moderator", "moderator_input", debate.moderator)
    debate.moderator = st.session_state.get("moderator_input", "")

    st.pills(
        "Mode",
        key="mode_input",
        options=["Roleplay"],
        default=debate.mode if debate.mode and len(debate.mode) else None,
    )
    debate.mode = st.session_state.get("mode_input", "")

    if st.button("Start"):
        validation = DebateValidation(debate)
        if not validation.proponent:
            st.error("A proponent is needed")
        elif not validation.opponent:
            st.error("An opponent is needed")
        elif not validation.moderator:
            st.error("A moderator is needed")
        elif not validation.topic:
            st.error("A topic is needed")
        elif not validation.mode:
            st.error("A mode is needed")
        else:
            State.save_debate()
            debate.messages.clear()
            debate.active = True
            st.rerun()
