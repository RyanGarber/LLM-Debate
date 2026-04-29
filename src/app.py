import streamlit as st
import dotenv

from data.debate import DebateValidation
from state import State
from ui.config import render_config
from ui.debate import render_debate
from ui.sidebar import render_sidebar

st.set_page_config(layout="centered", page_title="LLM Debate")

dotenv.load_dotenv()
State.load_debate()
State.update_models()

debate, models = State.get()

render_sidebar(debate)

if len(models) == 0:
    st.error("Error: No models available")
else:
    if DebateValidation(debate).all() and debate.active:
        render_debate(debate, models)
    else:
        render_config(debate, models)
