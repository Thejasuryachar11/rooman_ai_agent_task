# ARCHITECTURE.md

## Overview

This document describes the architecture of the **AI Support Assistant**, a Streamlit-based chatbot that answers user questions, uses a FAQ knowledge base, calls Gemini (Google Generative AI) for open-ended queries, and escalates complex/urgent issues to human support.

---

## High-Level Architecture

```
User → Streamlit UI → SupportAgent Logic
SupportAgent → FAQ Knowledge Base (local)
SupportAgent → Gemini API (google-generativeai)
SupportAgent → Escalation Handler (ticket / webhook)
```

The system follows a **3‑layer logic**:

1. **Fast Local Layer** – Greetings, quick replies, UI routing, FAQ matching.
2. **AI Reasoning Layer** – Calls Gemini when FAQ confidence is low.
3. **Escalation Layer** – Handles urgent or complex queries.

---

## Components

### 1. **Streamlit UI (`app.py`)**

* Renders chat interface.
* Maintains per‑session memory via `st.session_state`.
* Renders quick-action buttons.
* Handles New Chat, Clear Chat, End Chat.
* Sends user input to `SupportAgent` and displays responses.

### 2. **SupportAgent (`agent_logic.py`)**

Responsible for:

* Greeting detection
* Fuzzy FAQ matching
* Escalation keyword scanning
* Building prompts
* Calling Gemini via a robust model-calling wrapper
* Returning structured responses `(text, escalated, reason, actions)`

### 3. **Knowledge Base (`faq_kb.py`)**

* List of `{question, answer, category}` entries.
* Used with FuzzyWuzzy for approximate matching.

### 4. **Gemini API (google-generativeai)**

* Provides free-form conversational answers.
* `_call_model()` handles multiple possible SDK method names and fallbacks.
* Auto-detects usable models via `genai.list_models()`.

### 5. **Escalation Handler (internal)**

Triggered when:

* Escalation keywords appear ("urgent", "not working", "refund", etc.)
* Query is too complex (length heuristic)
* Gemini fails repeatedly

Escalation response includes:

* Escalation message
* Ticket ID
* Escalation reason

---



## Data Flow

1. User message → added to session state.
2. Message passed to SupportAgent.
3. SupportAgent:

   * Checks greeting → instant UI reply
   * Runs FAQ fuzzy matching → returns FAQ if high confidence
   * Builds prompt and calls Gemini → returns AI answer
   * If escalation case → returns escalation message
4. Final structured result → appended to chat and rendered.

---

## Security & Key Management

* Secrets stored in environment variables (`GEMINI_API_KEY`).
* Avoid logging full raw queries in production.
* HTTPS required in deployment.

---

