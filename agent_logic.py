# agent_logic.py
"""
SupportAgent with safe/robust Gemini integration.

- If google.generativeai is not installed or GEMINI_API_KEY is missing, the agent
  runs in fallback mode (FAQ + local behavior) and does NOT crash the app.
- When the SDK + key are available, the agent auto-selects a model and uses
  a resilient caller to attempt different call signatures.
"""

import os
from typing import Optional, Tuple, List
from fuzzywuzzy import fuzz

# Try to import the Gemini SDK; handle gracefully if not present.
try:
    import google.generativeai as genai  # type: ignore
    GEMINI_SDK_AVAILABLE = True
except Exception as e:
    genai = None  # type: ignore
    GEMINI_SDK_AVAILABLE = False
    print("[agent_logic] google.generativeai not available:", repr(e))

# optional dotenv (non-fatal)
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

# Read API key from env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure genai only if available and key present
if GEMINI_SDK_AVAILABLE and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print("[agent_logic] genai.configure failed:", repr(e))
        GEMINI_SDK_AVAILABLE = False

# Preferred generation method names (try in order)
PREFERRED_METHODS = [
    "generate_content",
    "generateContent",
    "generate_text",
    "generateText",
    "generate",
]

# Candidate model name filters (preference order)
PREFERRED_MODEL_KEYWORDS = ["gemini", "chat-bison", "text-bison", "bison", "gpt", "llama"]


def _select_model_and_method() -> Tuple[Optional[str], Optional[str]]:
    """
    Query genai.list_models() and pick a model name and a supported method.
    If genai isn't available, return (None, None).
    """
    if not GEMINI_SDK_AVAILABLE:
        return None, None

    try:
        models = genai.list_models()
    except Exception as e:
        print("[agent_logic] list_models() failed:", repr(e))
        return None, None

    candidates = []
    for m in models:
        # model object shape may vary by SDK version; try common attributes
        name = getattr(m, "name", None) or getattr(m, "model", None) or None
        if not name:
            continue
        score = 0
        lname = name.lower()
        for i, kw in enumerate(PREFERRED_MODEL_KEYWORDS):
            if kw in lname:
                score += (len(PREFERRED_MODEL_KEYWORDS) - i) * 10
        supported = getattr(m, "supported_generation_methods", None) or getattr(m, "generation_methods", None) or []
        candidates.append((score + (len(supported) if supported else 0), m))

    candidates.sort(key=lambda x: x[0], reverse=True)

    for _, m in candidates:
        name = getattr(m, "name", None) or getattr(m, "model", None)
        supported = getattr(m, "supported_generation_methods", None) or getattr(m, "generation_methods", None) or []
        supported_norm = [str(s) for s in supported]
        for method in PREFERRED_METHODS:
            for s in supported_norm:
                if method.lower() in s.lower() or s.lower() in method.lower():
                    return name, method
        if supported_norm:
            return name, supported_norm[0]

    return None, None


# Determine model+method once on import (if possible)
_SELECTED_MODEL_NAME, _SELECTED_METHOD = _select_model_and_method()

if _SELECTED_MODEL_NAME:
    try:
        print(f"[agent_logic] Selected model: {_SELECTED_MODEL_NAME}  method: {_SELECTED_METHOD}")
    except Exception:
        pass
else:
    try:
        print("[agent_logic] No suitable Gemini model found at startup; running in fallback mode.")
    except Exception:
        pass


class SupportAgent:
    def __init__(self, faq_database):
        self.faq_db = faq_database
        self.escalation_threshold = 0.6
        self.model_name = _SELECTED_MODEL_NAME
        self.method_name = _SELECTED_METHOD
        # llm_available only if SDK + key + selected model exist
        self.llm_available = bool(GEMINI_SDK_AVAILABLE and GEMINI_API_KEY and self.model_name)
        self.system_instruction = (
            "You are a friendly, expert AI assistant. Answer conversationally like ChatGPT. "
            "Ask clarification questions when helpful and offer follow-up help."
        )

        if not self.llm_available:
            print("[agent_logic] LLM is NOT available. Agent will use FAQ/local fallbacks.")

    # -----------------------
    # helpers
    # -----------------------
    def _is_greeting(self, query: str) -> bool:
        return query.strip().lower() in {"hi", "hello", "hey", "hii", "hola", "yo", "hiya"}

    def find_matching_faq(self, query: str) -> Tuple[Optional[dict], float]:
        best_match = None
        best_score = 0
        q = query.lower()
        for faq in self.faq_db:
            score = fuzz.token_set_ratio(q, faq.get("question", "").lower())
            if score > best_score:
                best_score = score
                best_match = faq
        if best_score >= 60:
            return best_match, best_score / 100.0
        return None, 0.0

    def detect_escalation_keywords(self, query: str) -> bool:
        keywords = [
            "urgent",
            "critical",
            "emergency",
            "asap",
            "immediately",
            "broken",
            "not working",
            "error",
            "angry",
            "refund",
            "cancel",
            "speak to",
            "human",
            "manager",
            "lawsuit",
        ]
        q = query.lower()
        return any(k in q for k in keywords)

    # -----------------------
    # call Gemini robustly (only used if llm_available True)
    # -----------------------
    def _call_model(self, prompt: str) -> str:
        if not self.llm_available:
            raise RuntimeError("Gemini model not configured or API key missing")

        # instantiate model object where possible
        model = None
        try:
            model = genai.GenerativeModel(self.model_name)
        except Exception:
            model = None

        def _extract_text(resp):
            if isinstance(resp, str):
                return resp
            if hasattr(resp, "text") and isinstance(resp.text, str):
                return resp.text
            if hasattr(resp, "content") and isinstance(resp.content, str):
                return resp.content
            if isinstance(resp, dict):
                for k in ("text", "content", "output", "outputs", "candidates", "message", "messages"):
                    if k in resp:
                        val = resp[k]
                        if isinstance(val, list) and val:
                            first = val[0]
                            if isinstance(first, dict):
                                for kk in ("text", "content", "message"):
                                    if kk in first and isinstance(first[kk], str):
                                        return first[kk]
                                try:
                                    return str(first)
                                except Exception:
                                    pass
                            elif isinstance(first, str):
                                return first
                        elif isinstance(val, str):
                            return val
                try:
                    return str(resp)
                except Exception:
                    pass
            if hasattr(resp, "outputs"):
                outputs = getattr(resp, "outputs")
                if outputs:
                    out0 = outputs[0]
                    if hasattr(out0, "text") and isinstance(out0.text, str):
                        return out0.text
                    if hasattr(out0, "content"):
                        try:
                            c = out0.content
                            if isinstance(c, list) and c:
                                first = c[0]
                                if isinstance(first, dict):
                                    for kk in ("text", "content", "message"):
                                        if kk in first and isinstance(first[kk], str):
                                            return first[kk]
                        except Exception:
                            pass
            if hasattr(resp, "candidates"):
                cands = getattr(resp, "candidates")
                if isinstance(cands, list) and cands:
                    cand0 = cands[0]
                    if isinstance(cand0, dict):
                        for kk in ("output", "content", "text"):
                            if kk in cand0 and isinstance(cand0[kk], str):
                                return cand0[kk]
                    if hasattr(cand0, "text") and isinstance(cand0.text, str):
                        return cand0.text
            return None

        attempts = []

        if model is not None:
            method_variants = [
                ("generate_content", {"prompt": prompt}),
                ("generate_content", {"input": prompt}),
                ("generate_content", {"messages": [{"role": "user", "content": prompt}]}),
                ("generateContent", {"prompt": prompt}),
                ("generateContent", {"input": prompt}),
                ("generateContent", {"messages": [{"role": "user", "content": prompt}]}),
                ("generate_text", {"prompt": prompt}),
                ("generate_text", {"text": prompt}),
                ("generate_text", {"input": prompt}),
                ("generateText", {"text": prompt}),
                ("generate", {"prompt": prompt}),
                ("generate", {"input": prompt}),
                ("create", {"prompt": prompt}),
            ]

            for method, kwargs in method_variants:
                if hasattr(model, method):
                    func = getattr(model, method)
                    attempts.append((func, kwargs))
            for method, _ in method_variants:
                if hasattr(model, method):
                    func = getattr(model, method)
                    attempts.append((func, (prompt,)))

        top_level_variants = [
            ("generate_content", {"model": self.model_name, "prompt": prompt}),
            ("generate_content", {"model": self.model_name, "input": prompt}),
            ("generate_content", {"model": self.model_name, "messages": [{"role": "user", "content": prompt}]}),
            ("generateContent", {"model": self.model_name, "prompt": prompt}),
            ("generate_text", {"model": self.model_name, "prompt": prompt}),
            ("generate_text", {"model": self.model_name, "text": prompt}),
            ("generate_text", {"model": self.model_name, "input": prompt}),
            ("generate", {"model": self.model_name, "prompt": prompt}),
            ("generate", {"model": self.model_name, "input": prompt}),
            ("create", {"model": self.model_name, "prompt": prompt}),
        ]
        for fname, kwargs in top_level_variants:
            if GEMINI_SDK_AVAILABLE and hasattr(genai, fname):
                attempts.append((getattr(genai, fname), kwargs))

        generic_fallbacks = [
            (getattr(genai, "generate", None), {"model": self.model_name, "prompt": prompt}) if GEMINI_SDK_AVAILABLE else (None, None),
            (getattr(genai, "generate_text", None), {"model": self.model_name, "prompt": prompt}) if GEMINI_SDK_AVAILABLE else (None, None),
            (getattr(genai, "generate_content", None), {"model": self.model_name, "prompt": prompt}) if GEMINI_SDK_AVAILABLE else (None, None),
        ]
        for f, kw in generic_fallbacks:
            if f:
                attempts.append((f, kw))

        errors = []
        for func, args in attempts:
            if not func:
                continue
            try:
                if isinstance(args, tuple):
                    resp = func(*args)
                elif isinstance(args, dict):
                    try:
                        resp = func(**args)
                    except TypeError:
                        try:
                            resp = func(args)
                        except Exception:
                            raise
                else:
                    resp = func(prompt)
            except Exception as e:
                errors.append(e)
                continue

            text = _extract_text(resp)
            if text:
                return text
            try:
                s = str(resp)
                if s and s.strip() and len(s.strip()) > 10:
                    return s.strip()
            except Exception:
                pass

        last_err = errors[-1] if errors else None
        raise RuntimeError(f"All model call attempts failed. Last error: {repr(last_err)}")

    # -----------------------
    # main logic
    # -----------------------
    def process_query(self, user_query: str) -> Tuple[str, bool, Optional[str], Optional[List[str]]]:
        q = (user_query or "").strip()
        if not q:
            return "Please type your question so I can help you.", False, None, None

        # Instant greetings
        if self._is_greeting(q):
            return (
                "Hi there! 👋 I'm your assistant — how can I help today?",
                False,
                None,
                ["Check FAQs", "Report an issue", "Talk to a human"],
            )

        # Escalation detection
        if self.detect_escalation_keywords(q):
            return (
                "This looks urgent. I'm escalating this to a human support agent.",
                True,
                "Contains urgent/critical keywords",
                None,
            )

        # FAQ matching
        faq, confidence = self.find_matching_faq(q)
        faq_context = None
        if faq:
            faq_context = f"FAQ: {faq.get('question')}\nAnswer: {faq.get('answer')}"

        # If high-confidence FAQ, return directly
        if faq and confidence >= 0.75:
            reply = (
                f"Based on our knowledge base:\n\nQ: {faq.get('question')}\nA: {faq.get('answer')}\n\n"
                "Would you like more details or to talk to a human?"
            )
            return reply, False, None, None

        # Prepare prompt for model
        prompt = self.system_instruction + "\n\n"
        if faq_context:
            prompt += f"Relevant FAQ context:\n{faq_context}\n\n"
        prompt += f"User: {q}\nAssistant:"

        # Try to call model; if fails, fallback gracefully
        if self.llm_available:
            try:
                answer_text = self._call_model(prompt)
                if answer_text and answer_text.strip():
                    return answer_text.strip(), False, None, None
            except Exception as e:
                try:
                    print("[agent_logic] model call failed:", repr(e))
                except Exception:
                    pass

        # Medium-confidence FAQ fallback
        if faq and confidence >= 0.5:
            reply = (
                f"It looks like this FAQ might help:\n\nQ: {faq.get('question')}\nA: {faq.get('answer')}\n\n"
                "If that doesn't answer your question, reply and I'll connect you to support."
            )
            return reply, False, None, None

        # Generic fallback when model unavailable
        fallback = (
            "Sorry — I can't generate a full answer right now. I can show relevant FAQs or connect you to human support. "
            "Which would you prefer?"
        )
        return fallback, False, None, ["Show FAQs", "Talk to human"]
