import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="SA PrepBot", page_icon="🚨", layout="centered")

st.title("🚨 SA PrepBot")
st.caption("San Antonio emergency preparedness assistant — grounded in official City of San Antonio (COSA) sources.")

if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role": "human"|"bot", "text": "..."}]

for msg in st.session_state.messages:
    role = "user" if msg["role"] == "human" else "assistant"
    with st.chat_message(role):
        st.markdown(msg["text"])
        if msg.get("sources"):
            with st.expander("Sources"):
                for src in msg["sources"]:
                    score_str = f" (score: {src['score']})" if src.get("score") is not None else ""
                    st.markdown(f"**[{src['id']}]** {src['url']}{score_str}\n\n> {src['snippet']}")

question = st.chat_input("Ask about emergency preparedness in San Antonio...")

if question:
    st.session_state.messages.append({"role": "human", "text": question})
    with st.chat_message("user"):
        st.markdown(question)

    history_payload = [
        {"role": m["role"], "text": m["text"]}
        for m in st.session_state.messages[:-1]
    ]

    with st.chat_message("assistant"):
        with st.spinner("Checking COSA sources..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/ask",
                    json={"question": question, "history": history_payload},
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                data = {"answer": f"Error contacting SA PrepBot backend: {e}", "sources": []}

        st.markdown(data["answer"])
        if data.get("sources"):
            with st.expander("Sources"):
                for src in data["sources"]:
                    score_str = f" (score: {src['score']})" if src.get("score") is not None else ""
                    st.markdown(f"**[{src['id']}]** {src['url']}{score_str}\n\n> {src['snippet']}")

    st.session_state.messages.append(
        {"role": "bot", "text": data["answer"], "sources": data.get("sources", [])}
    )
