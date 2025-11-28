# app.py - Streamlit chat app with quick-actions, safe_rerun, and End Chat / Restart Chat behavior

import os
import streamlit as st
from datetime import datetime
from agent_logic import SupportAgent
from faq_kb import FAQ_DATABASE

# ---------------------------
# Helper: safe rerun across Streamlit versions
# ---------------------------
def safe_rerun():
    """
    Attempt to programmatically rerun the Streamlit script in a way that works across
    different Streamlit versions.
    """
    try:
        st.experimental_rerun()
    except Exception:
        try:
            from streamlit.runtime.scriptrunner import RerunException
            raise RerunException()
        except Exception:
            st.markdown("<script>window.location.reload()</script>", unsafe_allow_html=True)


# ---------------------------
# Page config & CSS
# ---------------------------
st.set_page_config(
    page_title="Support Assistant Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stChatMessage {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
    }
    .escalation-badge {
        background-color: #ff6b6b;
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }
    .resolved-badge {
        background-color: #51cf66;
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }
    .end-chat {
        background-color: #6c757d;
        color: white;
        padding: 6px 12px;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)


# ---------------------------
# Session state initialization
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "ticket_id" not in st.session_state:
    st.session_state.ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

if "escalated" not in st.session_state:
    st.session_state.escalated = False

if "chat_ended" not in st.session_state:
    st.session_state.chat_ended = False

# For quick-reply (action buttons)
if "quick_reply" not in st.session_state:
    st.session_state.quick_reply = None

# Guarded agent initialization so we don't recreate on each rerun
if "agent_initialized" not in st.session_state:
    st.session_state.agent_initialized = False

if not st.session_state.agent_initialized:
    try:
        if not os.getenv("GEMINI_API_KEY"):
            # show as a non-blocking warning; agent_logic may also validate on init
            st.warning("GEMINI_API_KEY not found in environment. Set it if required by your agent.")
        st.session_state.agent = SupportAgent(FAQ_DATABASE)
        st.session_state.agent_initialized = True
    except Exception as e:
        st.error(f"Failed to initialize SupportAgent: {e}")
        st.stop()


# ---------------------------
# Sidebar (with End Chat and Restart Chat)
# ---------------------------
with st.sidebar:
    st.title("Support Assistant")
    st.markdown("---")
    st.subheader("Ticket Information")
    st.info(f"**Ticket ID:** {st.session_state.ticket_id}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            st.session_state.escalated = False
            st.session_state.chat_ended = False
            st.session_state.quick_reply = None
            safe_rerun()

    with col2:
        if st.button("Clear History", use_container_width=True):
            st.session_state.messages = []
            safe_rerun()

    st.markdown("---")
    st.subheader("Status")
    if st.session_state.escalated:
        st.markdown('<div class="escalation-badge">ESCALATED TO AGENT</div>', unsafe_allow_html=True)
        st.warning("This issue has been escalated to a human support agent. They will contact you soon.")
    elif st.session_state.chat_ended:
        st.markdown('<div class="end-chat">CHAT ENDED</div>', unsafe_allow_html=True)
        st.info("You ended this chat. Use Restart Chat to begin a fresh conversation.")
    else:
        st.markdown('<div class="resolved-badge">RESOLVING</div>', unsafe_allow_html=True)
        st.success("AI Agent is handling your query.")

    st.markdown("---")
    st.subheader("Knowledge Base")
    st.write(f"📚 **Total FAQs:** {len(FAQ_DATABASE)}")
    st.write(f"📖 **Categories:** {len(set(faq.get('category', 'General') for faq in FAQ_DATABASE))}")

    with st.expander("View All FAQs"):
        for i, faq in enumerate(FAQ_DATABASE, 1):
            st.write(f"**{i}. {faq['question']}**")
            st.write(f"*Category: {faq.get('category', 'General')}*")

    st.markdown("---")
    # End Chat and Restart Chat controls
    if not st.session_state.chat_ended:
        if st.button("End Chat", key="sidebar_end_chat", use_container_width=True):
            # Append a polite closing assistant message and mark chat ended
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Thank you for chatting with us! If you have more questions later, just start a new chat. Have a great day! 😊",
                "escalation_reason": None,
                "actions": None
            })
            st.session_state.chat_ended = True
            safe_rerun()
    else:
        if st.button("Restart Chat", key="sidebar_restart", use_container_width=True):
            st.session_state.messages = []
            st.session_state.ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            st.session_state.escalated = False
            st.session_state.chat_ended = False
            st.session_state.quick_reply = None
            safe_rerun()


# ---------------------------
# Main chat interface
# ---------------------------
st.header("AI Support Assistant")
st.write("Hello! I'm your AI support assistant. I can help you with common questions and issues. If I can't resolve your problem, I'll escalate it to a human agent.")

# ---------------------------
# Display chat history (render actions if present)
# ---------------------------
for idx, message in enumerate(st.session_state.messages):
    role = message.get("role", "assistant")
    content = message.get("content", "")
    esc = message.get("escalation_reason")
    actions = message.get("actions")

    try:
        with st.chat_message(role):
            st.markdown(content)
            if esc:
                st.info(f"📌 Escalation Reason: {esc}")

            if role == "assistant" and actions:
                st.write("")
                # render horizontally if <=5 actions, else vertically
                if len(actions) <= 5:
                    cols = st.columns(len(actions))
                    for i, action in enumerate(actions):
                        btn_key = f"quick_action_{idx}_{i}_{st.session_state.ticket_id}"
                        if cols[i].button(action, key=btn_key):
                            st.session_state.quick_reply = action
                            # do not append extra messages here; let main input loop handle it
                            safe_rerun()
                else:
                    for i, action in enumerate(actions):
                        btn_key = f"quick_action_{idx}_{i}_{st.session_state.ticket_id}"
                        if st.button(action, key=btn_key):
                            st.session_state.quick_reply = action
                            safe_rerun()
    except Exception:
        st.markdown(f"**{role.upper()}**: {content}")
        if esc:
            st.info(f"📌 Escalation Reason: {esc}")


# ---------------------------
# Inline End Chat button below messages (for convenience)
# ---------------------------
if not st.session_state.chat_ended and not st.session_state.escalated:
    inline_col1, inline_col2 = st.columns([1, 3])
    with inline_col1:
        if st.button("End Chat", key="inline_end"):
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Thank you for chatting with us! If you have more questions later, just start a new chat. Have a great day! 😊",
                "escalation_reason": None,
                "actions": None
            })
            st.session_state.chat_ended = True
            safe_rerun()
    with inline_col2:
        # show a small hint / quick-action suggestion
        st.write("Need help? Type your question or use the quick-action buttons above.")


# ---------------------------
# DISPLAY CHAT HISTORY (with action buttons)
# ---------------------------
for idx, message in enumerate(st.session_state.messages):
    role = message.get("role", "assistant")
    content = message.get("content", "")
    esc = message.get("escalation_reason")
    actions = message.get("actions")

    try:
        with st.chat_message(role):
            st.markdown(content)
            if esc:
                st.info(f"📌 Escalation Reason: {esc}")

            # Render action buttons (if assistant provided any)
            if role == "assistant" and actions:
                st.write("")
                # horizontal if small number, else vertical
                if len(actions) <= 5:
                    cols = st.columns(len(actions))
                    for i, action in enumerate(actions):
                        btn_key = f"quick_action_{idx}_{i}_{st.session_state.ticket_id}"
                        if cols[i].button(action, key=btn_key):
                            # set quick_reply and let the run finish — Streamlit auto-reruns
                            st.session_state.quick_reply = action
                else:
                    for i, action in enumerate(actions):
                        btn_key = f"quick_action_{idx}_{i}_{st.session_state.ticket_id}"
                        if st.button(action, key=btn_key):
                            st.session_state.quick_reply = action

    except Exception:
        st.markdown(f"**{role.upper()}**: {content}")
        if esc:
            st.info(f"📌 Escalation Reason: {esc}")

# ---------------------------
# CHAT INPUT HANDLING (replace your previous block with this)
# ---------------------------
# Ensure processing lock exists
if "processing" not in st.session_state:
    st.session_state.processing = False

if not st.session_state.escalated and not st.session_state.chat_ended:
    # 1) If a quick_reply exists (set by clicking a button in previous run or current run),
    #    consume it immediately as the user_input for this run.
    if st.session_state.get("quick_reply"):
        user_input = st.session_state.quick_reply
        # show to user so they see what was selected
        st.info(f"Quick action selected: **{user_input}**")
        # clear quick_reply so we don't reuse it in subsequent reruns
        st.session_state.quick_reply = None
    else:
        # 2) Otherwise, show normal chat input
        user_input = st.chat_input("Type your question or issue here...")

    # 3) Process the input synchronously in this run (no safe_rerun after appending assistant response)
    if user_input and not st.session_state.processing:
        st.session_state.processing = True

        # Append user message right away (so it shows)
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        # Determine whether to skip spinner for greetings
        is_greeting = isinstance(user_input, str) and user_input.strip().lower() in ["hi", "hello", "hey", "hii"]

        # Call agent synchronously and capture result (handle 3- or 4-tuple)
        try:
            if is_greeting:
                result = st.session_state.agent.process_query(user_input)
            else:
                with st.spinner("AI agent is thinking..."):
                    result = st.session_state.agent.process_query(user_input)
        except Exception as e:
            # On any exception, return a friendly fallback and escalate
            result = ("Sorry — I couldn't process your request due to a backend error.", True, f"Processing error: {e}", None)

        # Normalize result
        if isinstance(result, tuple) and len(result) == 4:
            response_text, is_escalated, escalation_reason, actions = result
        elif isinstance(result, tuple) and len(result) == 3:
            response_text, is_escalated, escalation_reason = result
            actions = None
        else:
            response_text = str(result)
            is_escalated = False
            escalation_reason = None
            actions = None

        # Append assistant response in the same run (important!)
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "escalation_reason": escalation_reason if is_escalated else None,
            "actions": actions
        })

        # Update escalation / flags
        if is_escalated:
            st.session_state.escalated = True

        # release processing lock
        st.session_state.processing = False

        # DO NOT call safe_rerun() or st.rerun() here — let the current run render everything.
else:
    # if escalated or chat ended, show appropriate messages (input disabled)
    if st.session_state.escalated:
        st.info("This conversation has been escalated to a human support agent. Thank you for your patience!")
    elif st.session_state.chat_ended:
        st.info("Chat ended. Use 'Restart Chat' in the sidebar to start a new conversation.")
