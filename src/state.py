import json
import os

import requests
import streamlit as st
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.azure import AzureProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from data.message import Model
from data.debate import Debate


class State:
    @staticmethod
    def get() -> tuple[Debate, list[Model]]:
        if "session" not in st.session_state:
            st.session_state["session"] = Debate()
        if "models" not in st.session_state:
            st.session_state["models"] = []
        return st.session_state["session"], st.session_state["models"]

    @staticmethod
    def load_debate():
        debate, _ = State.get()
        if os.path.exists("./debate.json"):
            with open("./debate.json") as f:
                data = json.load(f)
                loaded = Debate.from_saved(data)
                debate.proponent = loaded.proponent
                debate.opponent = loaded.opponent
                debate.moderator = loaded.moderator
                debate.topic = loaded.topic
                debate.mode = loaded.mode

    @staticmethod
    def save_debate():
        debate, _ = State.get()
        with open("./debate.json", "w") as f:
            json.dump(debate.to_saved(), f)

    @staticmethod
    @st.cache_resource
    def update_models():
        print("[State] Loading models...")
        _, models = State.get()

        models.clear()

        if os.getenv("GOOGLE_API_KEY"):
            result = requests.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={os.getenv("GOOGLE_API_KEY")}"
            ).json()

            for model in result.get("models", []):
                if "generateContent" in model["supportedGenerationMethods"]:
                    models.append(
                        Model(
                            name=model["name"].replace("models/", "google/"),
                            provider=GoogleModel(
                                model_name=model["name"],
                                provider=GoogleProvider(
                                    api_key=os.getenv("GOOGLE_API_KEY")
                                ),
                            ),
                            supports_system_prompt="gemini" in model["name"].lower(),
                        )
                    )

        if os.getenv("AZURE_API_KEY"):
            azure_key = os.getenv("AZURE_API_KEY").split(",")
            result = requests.get(
                f"https://{azure_key[1]}.services.ai.azure.com/api/projects/{azure_key[0]}/deployments?api-version=v1",
                headers={"Authorization": f"Bearer {azure_key[2]}"},
            ).json()

            for model in result.get("value", []):
                if model["capabilities"]["chat_completion"]:
                    models.append(
                        Model(
                            name=f"azure/{model["name"]}",
                            provider=OpenAIChatModel(
                                model_name=model["name"],
                                provider=AzureProvider(
                                    azure_endpoint=f"https://{azure_key[1]}.services.ai.azure.com/openai/v1/",
                                    api_key=azure_key[2],
                                ),
                            ),
                            supports_system_prompt=True,
                        )
                    )

        if os.getenv("CUSTOM_API"):
            result = requests.get(os.getenv("CUSTOM_API") + "models").json()

            for model in result.get("data", []):
                models.append(
                    Model(
                        name=f"custom/{model["id"]}",
                        provider=OpenAIChatModel(
                            model_name=model["id"],
                            provider=OpenAIProvider(base_url=os.getenv("CUSTOM_API")),
                        ),
                        supports_system_prompt=True,
                    )
                )

        print(f"[State] {len(models)} models available")
