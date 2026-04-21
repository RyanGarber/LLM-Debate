import asyncio
from typing import NamedTuple
from time import sleep, time

import dotenv
import os
import ai_sdk
import streamlit as st
import json
import requests
from ai_sdk.providers.gemini import gemini
from ai_sdk.ui_stream import UITextDeltaPart

dotenv.load_dotenv()


def supports_system_prompt(name):
    return "gemini" in name


def system_prompt(name, role):
    prompt = f"Your name is {name}.\n"
    prompt += f"You are a {role} in a debate.\n"
    prompt += (
        f"The debaters in the debate are: {', '.join(st.session_state.debaters)}.\n"
    )
    prompt += f"The moderator of the debate is: {st.session_state.moderator}.\n"

    if role == "debater":
        prompt += "Form and argue your own position based on the topic and other debaters' previous statements.\n"
        prompt += "You should be persuasive and use facts and logic to support your position.\n"
        # prompt += "You should also try to anticipate and counter the arguments of the other debaters.\n"
        # prompt += "Your goal is to win the debate by convincing the moderator that your argument is the strongest."
    elif role == "moderator":
        prompt += "You will be given a topic and a list of debaters.\n"
        prompt += "Your job is to facilitate the debate and determine the winner.\n"
        # prompt += "You should ask each debater to make their opening statement, then allow for rebuttals and counterarguments.\n"
        # prompt += "At the end of the debate, you should determine the winner based on the strength of their arguments and how well they countered the other debaters."

    prompt += f"CRITICAL: It is now your turn. Only speak as yourself ({name}), no one else.\n"

    return prompt


_ = """ INIT """


# Model details
class Model:
    def __init__(self, name: str, provider):
        self.name = name
        self.provider = provider


# Load models with caching each session
@st.cache_resource
def load_models():
    print("Loading models...")
    models: list[Model] = []

    google = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models?key="
        + os.getenv("GOOGLE_API_KEY")
    ).json()

    for model in google.get("models", []):
        if "generateContent" in model["supportedGenerationMethods"]:
            models.append(
                Model(
                    model["name"].replace("models/", "google/"),
                    gemini(model["name"], api_key=os.getenv("GOOGLE_API_KEY")),
                )
            )

    return models


def get_model(name: str):
    for model in models:
        if model.name == name:
            return model
    raise ValueError(f"Model {name} not found")


_ = """ CONFIG """


# Whether config is valid
class ConfigValidity(NamedTuple):
    valid: bool
    debaters_valid: bool
    moderator_valid: bool
    topic_valid: bool
    mode_valid: bool


# Load config state from file
def load_config():
    global config

    with open("config.json") as f:
        config = json.load(f) if os.path.exists("config.json") else {}
    if "debaters" not in st.session_state and "debaters" in config:
        st.session_state.debaters = config["debaters"]
    if "moderator" not in st.session_state and "moderator" in config:
        st.session_state.moderator = config["moderator"]
    if "topic" not in st.session_state and "topic" in config:
        st.session_state.topic = config["topic"]
    if "mode" not in st.session_state and "mode" in config:
        st.session_state.mode = config["mode"]


# Check if config is valid
def check_config():
    debaters_valid = (
        st.session_state.get("debaters", []) and len(st.session_state.debaters) >= 2
    )
    moderator_valid = st.session_state.get("moderator", "") != ""
    topic_valid = st.session_state.get("topic", "") != ""
    mode_valid = st.session_state.get("mode", "") != ""
    valid = debaters_valid and moderator_valid and topic_valid
    return ConfigValidity(
        valid, debaters_valid, moderator_valid, topic_valid, mode_valid
    )


# Save config state to file
def save_config():
    config = {
        "debaters": st.session_state.debaters,
        "moderator": st.session_state.moderator,
        "topic": st.session_state.topic,
        "mode": st.session_state.mode,
    }
    with open("config.json", "w") as f:
        json.dump(config, f)


_ = """ STREAM """


def stream_sync(model, prompt, system=None, messages=None):
    async def create_stream():
        result = ai_sdk.stream_text(
            model=model, prompt=prompt, system=system, messages=messages
        )
        async for chunk in result.full_stream:
            if isinstance(chunk, UITextDeltaPart):
                yield chunk.delta

    loop = asyncio.new_event_loop()
    stream = create_stream()

    try:
        while True:
            try:
                yield loop.run_until_complete(stream.__anext__())
            except StopAsyncIteration:
                break
    finally:
        loop.close()


_ = """ APP """


# Show sidebar
def show_sidebar():
    with st.sidebar:
        if st.button(label="Reload Models", width="stretch"):
            load_models.clear()
            load_models()
            st.rerun()

        if "messages" in st.session_state:
            next_turn = "next_turn" in st.session_state and st.session_state.next_turn
            if not next_turn and st.button(label="Next Turn", width="stretch"):
                st.session_state.next_turn = True
                st.rerun()
            if st.button(label="New Debate", width="stretch"):
                st.session_state.pop("messages")
                st.rerun()


# Message details
class Message:
    def __init__(
        self, role: str, model: str, content: str = None, duration: float = None
    ):
        self.role = role
        self.model = model
        self.content = content
        self.duration = duration


# Config page
def show_config():
    with st.container():
        st.multiselect("Debaters", key="debaters", options=(m.name for m in models))
    st.selectbox("Moderator", key="moderator", options=(m.name for m in models))
    st.text_input("Topic", key="topic")
    st.pills("Mode", key="mode", options=["Roleplay", "Objective"])
    if st.button("Start"):
        _, debaters_valid, moderator_valid, topic_valid, mode_valid = check_config()
        if not debaters_valid:
            st.error("At least two debaters are needed")
        elif not moderator_valid:
            st.error("A moderator is needed")
        elif not topic_valid:
            st.error("A topic is needed")
        elif not mode_valid:
            st.error("A topic is needed")
        else:
            save_config()
            st.session_state.messages = []
            st.session_state.next_turn = True

            # Fix for ghost ui
            st.empty()
            sleep(0.1)
            st.rerun()


# Debate page
def show_debate():
    with st.chat_message(name="user"):
        st.markdown(st.session_state.topic)

    if "next_turn" in st.session_state and st.session_state.next_turn:
        print("Starting next turn...")
        next_debater = len(st.session_state.messages) % len(st.session_state.debaters)
        st.session_state.messages.append(
            Message("debater", st.session_state.debaters[next_debater])
        )

    for message in st.session_state.messages:
        with st.chat_message(name=message.role):
            if message.content is not None:
                with st.status(message.model, state="complete"):
                    st.html(f"Took {message.duration:.0f} seconds")
                st.markdown(message.content)
            else:
                start = time()
                st.session_state.next_turn = False

                prompt = ""
                system = system_prompt(message.model, message.role)
                if not supports_system_prompt(message.model):
                    prompt += f"System instructions:\n{system}\n\n"
                    system = None
                prompt += f"The topic is: {st.session_state.topic}"

                if len(st.session_state.messages) > 1:
                    prompt += "\n\nThe debate so far:"
                    for m in st.session_state.messages:
                        if m.content is not None:
                            prompt += f"\n\n[{m.role}:name={m.model}]\n{m.content}"

                print(f"Calling {message.role} ({message.model})\n")
                stream = stream_sync(get_model(message.model).provider, prompt, system)

                with st.status(message.model):
                    st.html(f"{time() - start:.0f} seconds")

                message.content = st.write_stream(stream)
                message.duration = time() - start

                st.rerun()


_ = """ MAIN """

# Initialize app
models = load_models()
load_config()

# Setup app
st.set_page_config(
    layout="centered",
    page_title="LLM Debate",
)

# Run app
show_sidebar()
if not check_config().valid or "messages" not in st.session_state:
    show_config()
else:
    show_debate()
