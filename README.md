# README.md

# AI Support Assistant

A full-featured conversational AI support agent built using **Streamlit**, **Gemini (Google Generative AI)**, and a **local FAQ knowledge base**. It behaves like a real chatbot, answers questions conversationally, suggests quick actions, and escalates complex or urgent issues to human support.

https://thejasuryachar11-rooman-ai-agent-task-app-3tvoyv.streamlit.app/

---

## 🚀 Features

### ✅ ChatGPT‑style conversational responses (Gemini powered)

### ✅ FAQ matching using fuzzy logic

### ✅ Quick-action buttons for instant help

### ✅ Auto-escalation for urgent queries

### ✅ Inline ticket generation

### ✅ Session-based chat memory

### ✅ Robust fallback if Gemini API fails

### ✅ Clean UI with Streamlit

---

## 📁 Project Structure

```
├── app.py                 # Frontend Streamlit UI
├── agent_logic.py         # Core logic: FAQ, Gemini, escalation, greetings
├── faq_kb.py              # Knowledge base (list of FAQ entries)
├── ARCHITECTURE.md        # Architecture & flowchart
├── DEPLOYMENT.md          # Deployment instructions
├── README.md              # This file
└── requirements.txt        # Python dependencies
```

---

## 🧩 How It Works

### 1. **User enters a query**

Message is appended instantly to the UI.

### 2. **SupportAgent processes the message**

* Detects greetings
* Matches FAQ using fuzzy scoring
* Detects escalation keywords (urgent, refund, error, etc.)
* Calls Gemini API using a robust multi-method fallback

### 3. **Returns a structured response**

Response is a tuple:

```
(text, is_escalated, escalation_reason, actions)
```

### 4. **UI renders the response**

* Displays the message
* Shows action buttons (if any)
* Disables input if escalated or ended

---

## 🔧 Setup Instructions

### 1. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Add Your Gemini API Key

```bash
export GEMINI_API_KEY="your_key_here"
```

Or create a `.env` file:

```
GEMINI_API_KEY=your_key_here
```

### 4. Run the App

```bash
streamlit run app.py
```

Your chatbot will open at:

```
http://localhost:8501
```

---

## 🐳 Docker Deployment (Short Version)

```bash
docker build -t ai-support .
docker run -p 8501:8501 -e GEMINI_API_KEY=$GEMINI_API_KEY ai-support
```

For complete deployment options, see **DEPLOYMENT.md**.

---

## ✨ Screenshots (Optional)

You can add:

* Chat UI example
* Flowchart image
* Architecture diagram

---

## 🤝 Contributing

PRs and improvements are welcome!

---

## 📜 License

MIT License (customize if needed)

---
