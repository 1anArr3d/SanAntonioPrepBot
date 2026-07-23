import html
import os
import re
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# JagUnify's maroon (#6b2f3c), kept for continuity — the campus photo background
# and mascot send-icon PNG it used are replaced with solid colors/plain markup
# below since we don't have SA PrepBot-specific art assets.
MAROON = "#6b2f3c"
MAROON_BUBBLE = "rgba(107, 47, 60, 0.78)"
AMBER = "#f5c451"
SOURCE_BLUE = "#bfdbfe"

st.set_page_config(page_title="SA PrepBot", layout="centered")

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {MAROON};
    }}
    #MainMenu, footer {{ visibility: hidden; }}

    .prepbot-header {{
        text-align: center;
        color: white;
        margin-bottom: 12px;
    }}
    .prepbot-header h1 {{
        margin-bottom: 2px;
        font-size: 2rem;
    }}
    .prepbot-header p {{
        margin: 0;
        opacity: 0.85;
        font-size: 0.95rem;
    }}

    .chat-panel {{
        background: rgba(255, 255, 255, 0.88);
        backdrop-filter: blur(2px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.4);
        box-shadow: rgba(0, 0, 0, 0.15) 0 10px 15px -3px;
        padding: 20px;
        max-height: 60vh;
        overflow-y: auto;
        margin-bottom: 14px;
    }}

    .msg-row {{
        display: flex;
        flex-direction: column;
        margin-bottom: 14px;
    }}
    .msg-row.human {{ align-items: flex-end; }}
    .msg-row.bot {{ align-items: flex-start; }}

    .bubble {{
        max-width: 75%;
        border-radius: 14px;
        padding: 10px 14px;
        color: white;
        background: {MAROON_BUBBLE};
        border: 1px solid rgba(0,0,0,0.1);
        line-height: 1.4;
    }}

    .msg-time {{
        font-size: 0.72rem;
        color: #4b3b40;
        margin-top: 3px;
        padding: 0 4px;
    }}

    .cite-link {{
        color: {AMBER};
        font-weight: 600;
        text-decoration: none;
    }}
    .cite-link:hover {{ text-decoration: underline; }}

    .sources-block {{
        margin-top: 10px;
        padding-top: 8px;
        border-top: 1px solid rgba(255,255,255,0.25);
        font-size: 0.78rem;
        color: {SOURCE_BLUE};
    }}
    .source-item {{ position: relative; margin-bottom: 4px; }}
    .source-item a {{ color: {SOURCE_BLUE}; text-decoration: underline; }}
    .source-preview {{
        display: none;
        position: absolute;
        left: 0;
        top: 100%;
        z-index: 50;
        width: 280px;
        margin-top: 4px;
        background: white;
        color: #27272a;
        border: 1px solid #d4d4d8;
        border-radius: 8px;
        padding: 10px;
        font-size: 0.75rem;
        box-shadow: rgba(0, 0, 0, 0.15) 0 10px 15px -3px;
    }}
    .source-item:hover .source-preview {{ display: block; }}

    .typing-row {{ display: flex; align-items: center; margin-bottom: 14px; }}
    .typing-dots {{
        display: inline-flex;
        background: {MAROON_BUBBLE};
        border-radius: 14px;
        padding: 12px 14px;
    }}
    .typing-dots span {{
        width: 6px;
        height: 6px;
        margin: 0 2px;
        border-radius: 50%;
        background: white;
        display: inline-block;
        animation: bounce 1.2s infinite;
    }}
    .typing-dots span:nth-child(2) {{ animation-delay: 0.15s; }}
    .typing-dots span:nth-child(3) {{ animation-delay: 0.3s; }}
    @keyframes bounce {{
        0%, 60%, 100% {{ transform: translateY(0); }}
        30% {{ transform: translateY(-4px); }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="prepbot-header">'
    "<h1>SA PrepBot</h1>"
    "<p>San Antonio emergency preparedness assistant — grounded in official City of San Antonio (COSA) sources.</p>"
    "</div>",
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "bot",
            "text": "Hey neighbor! How can I help you prepare?",
            "sources": [],
            "time": datetime.now().strftime("%I:%M %p").lstrip("0"),
        }
    ]

col1, col2 = st.columns([5, 1])
with col2:
    if st.button("Clear", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


def render_bot_text(text: str, sources: list) -> str:
    source_by_id = {s["id"]: s for s in (sources or [])}
    lines = []
    for line in text.split("\n"):
        tokens = re.split(r"(\*\*[^*]+\*\*|\[\d+\])", line)
        rendered = []
        for token in tokens:
            bold_match = re.match(r"^\*\*([^*]+)\*\*$", token)
            cite_match = re.match(r"^\[(\d+)\]$", token)
            if bold_match:
                rendered.append(f"<strong>{html.escape(bold_match.group(1))}</strong>")
            elif cite_match:
                cite_id = int(cite_match.group(1))
                source = source_by_id.get(cite_id)
                if source:
                    rendered.append(
                        f'<a class="cite-link" href="{html.escape(source["url"])}" target="_blank" rel="noreferrer">[{cite_id}]</a>'
                    )
                else:
                    rendered.append(html.escape(token))
            else:
                rendered.append(html.escape(token))
        lines.append("".join(rendered))
    return "<br>".join(lines)


def render_sources(sources: list) -> str:
    if not sources:
        return ""
    items = []
    for src in sources:
        snippet = html.escape(src.get("snippet") or "No preview available.")
        url = html.escape(src["url"])
        items.append(
            f'<div class="source-item">[{src["id"]}] '
            f'<a href="{url}" target="_blank" rel="noreferrer">{url}</a>'
            f'<div class="source-preview">{snippet}</div></div>'
        )
    return f'<div class="sources-block">{"".join(items)}</div>'


def render_message(msg: dict) -> str:
    is_human = msg["role"] == "human"
    row_class = "human" if is_human else "bot"
    if is_human:
        body = html.escape(msg["text"])
    else:
        body = render_bot_text(msg["text"], msg.get("sources", [])) + render_sources(msg.get("sources", []))
    time_str = msg.get("time", "")
    # No leading whitespace/newlines here — Streamlit's markdown parser treats
    # 4-space-indented lines as a code block and prints the raw tags as text.
    return (
        f'<div class="msg-row {row_class}">'
        f'<div class="bubble">{body}</div>'
        f'<div class="msg-time">{time_str}</div>'
        f"</div>"
    )


# Two-phase submit so the typing indicator actually has a chance to render:
# phase 1 stashes the question and reruns immediately (showing it + the dots),
# phase 2 (next script run) does the slow network call and appends the reply.
pending = st.session_state.get("pending_question")

chat_html = ['<div class="chat-panel">']
for msg in st.session_state.messages:
    chat_html.append(render_message(msg))
if pending:
    chat_html.append(
        '<div class="typing-row"><div class="typing-dots"><span></span><span></span><span></span></div></div>'
    )
chat_html.append("</div>")
st.markdown("".join(chat_html), unsafe_allow_html=True)

question = st.chat_input("Ask about emergency preparedness in San Antonio...")

if question:
    now_str = datetime.now().strftime("%I:%M %p").lstrip("0")
    st.session_state.messages.append({"role": "human", "text": question, "sources": [], "time": now_str})
    st.session_state.pending_question = question
    st.rerun()

if pending:
    history_payload = [
        {"role": m["role"], "text": m["text"]}
        for m in st.session_state.messages[:-1]
    ]

    try:
        resp = requests.post(
            f"{BACKEND_URL}/ask",
            json={"question": pending, "history": history_payload},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data or not data.get("answer"):
            raise ValueError("Empty response from backend.")
    except (requests.RequestException, ValueError) as e:
        data = {"answer": f"Error contacting SA PrepBot backend: {e}", "sources": []}

    st.session_state.messages.append(
        {
            "role": "bot",
            "text": data["answer"],
            "sources": data.get("sources", []),
            "time": datetime.now().strftime("%I:%M %p").lstrip("0"),
        }
    )
    st.session_state.pending_question = None
    st.rerun()
