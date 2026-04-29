import streamlit as st

from data.debate import Debate
from logic.message import create_next_message
from state import State


# Show sidebar
def render_sidebar(debate: Debate):
    with st.sidebar:
        if st.button(label="Reload Models", width="stretch"):
            State.update_models.clear()
            State.update_models()
            st.rerun()

        if debate.active:
            if st.button(label="Next Turn", width="stretch"):
                debate.messages.append(create_next_message(debate))
                st.rerun()
            if st.button(label="New Debate", width="stretch"):
                debate.active = False
                st.rerun()
