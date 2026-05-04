import json
import re
from typing import Optional, Any, Type

import httpx

from .config import cfg


class LLMClient:
    def __init__(self, endpoint: str = None, api_key: str = None, timeout: Optional[int] = None):
        self.endpoint = endpoint or cfg.LLAMA_ENDPOINT
        self.api_key = api_key or cfg.LLAMA_API_KEY
        self.timeout = timeout or int(getattr(cfg, "LLM_TIMEOUT", 120))
        self.client = httpx.Client(timeout=self.timeout)

    def call_llm(self, text: str, response_model: Optional[Type[Any]] = None, max_tokens: int = 256, max_retries: int = 1) -> dict:
        """Call the LLM and optionally validate/parse the JSON output with a Pydantic model.

        If `response_model` (a Pydantic BaseModel class) is provided, the parsed JSON
        will be validated and returned as the model instance (or its dict).
        """
        url = f"{self.endpoint}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        # Stronger prompt: system + user messages, request strict JSON and Japanese output
        system_msg = (
            "You are a concise summarization assistant. Respond only with valid JSON that exactly matches the schema:\n"
            "{\n  \"summary\": \"string\",\n  \"highlights\": [\"string\", ...],\n  \"importance\": \"integer (1-5)\"\n}\n"
            "Do not include any explanation, commentary, or extra text outside the JSON. Summarize the article in Japanese."
        )
        user_msg = "Article:\n```" + text + "```"
        # Prevent sending extremely long payloads which may be rejected by
        # some LLM endpoints. Truncate to a reasonable size.
        max_input_chars = 4000
        if len(text) > max_input_chars:
            text = text[:max_input_chars]
            prompt = (
                "You are a summarization assistant. Given the article text delimited by triple backticks, "
                "produce a JSON object with keys: summary (3 lines max), highlights (list of 3 bullets), importance (1-5 integer).\n"
                "If the article was truncated, indicate that in the summary.\n"
                "Return only valid JSON.\n\nArticle:\n```" + text + "```"
            )

        attempt = 0
        last_err = None
        while attempt <= max_retries:
            try:
                payload = {
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": max_tokens,
                }
                resp = self.client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                last_err = None
                break
            except Exception as e:
                last_err = e
                attempt += 1
                continue
        if last_err:
            try:
                err_text = getattr(last_err, "response", None) and last_err.response.text or str(last_err)
            except Exception:
                err_text = str(last_err)
            return {"summary": "", "error": str(last_err), "error_text": err_text}

        # Expect OpenAI-like response
        try:
            msg = data["choices"][0]["message"]
            # Prefer explicit assistant content, but some models place the useful
            # text in other fields like `reasoning_content`.
            content = msg.get("content") or msg.get("reasoning_content") or ""
        except Exception:
            content = json.dumps(data)

        def _extract_json_from_text(text: str):
            if not text:
                return None
            text = text.strip()
            # If entire text is JSON, try parse directly
            try:
                return json.loads(text)
            except Exception:
                pass

            # Common pattern: model returns explanation then a JSON block. Try to
            # find the first JSON object or array in the text.
            # This is a best-effort heuristic.
                # Try to find a balanced JSON object by scanning forward from each
                # opening brace. This handles nested braces correctly.
                for m in re.finditer(r"\{", text):
                    start = m.start()
                    depth = 0
                    for i in range(start, len(text)):
                        if text[i] == "{":
                            depth += 1
                        elif text[i] == "}":
                            depth -= 1
                            if depth == 0:
                                candidate = text[start : i + 1]
                                try:
                                    return json.loads(candidate)
                                except Exception:
                                    break

                # Try array similarly
                for m in re.finditer(r"\[", text):
                    start = m.start()
                    depth = 0
                    for i in range(start, len(text)):
                        if text[i] == "[":
                            depth += 1
                        elif text[i] == "]":
                            depth -= 1
                            if depth == 0:
                                candidate = text[start : i + 1]
                                try:
                                    return json.loads(candidate)
                                except Exception:
                                    break

            return None

        try:
            parsed = _extract_json_from_text(content)
            if parsed is None and isinstance(msg, dict):
                for key in ("reasoning_content", "content", "text", "output"):
                    txt = msg.get(key)
                    parsed = _extract_json_from_text(txt)
                    if parsed is not None:
                        break

            if parsed is not None:
                if response_model is not None:
                    try:
                        # Pydantic v2
                        if hasattr(response_model, "model_validate"):
                            validated = response_model.model_validate(parsed)
                            try:
                                return validated.model_dump()
                            except Exception:
                                return validated.dict()
                        # Pydantic v1 fallback
                        validated = response_model(**parsed)
                        return validated.dict()
                    except Exception as e:
                        return {"summary": "", "validation_error": str(e), "raw": parsed}
                return parsed

            fallback = msg.get("content") or msg.get("reasoning_content") or ""
            if response_model is not None:
                try:
                    if hasattr(response_model, "model_validate"):
                        inst = response_model.model_validate({"summary": fallback})
                        try:
                            return inst.model_dump()
                        except Exception:
                            return inst.dict()
                    inst = response_model(summary=fallback)
                    return inst.dict()
                except Exception:
                    return {"summary": fallback}

            return {"summary": fallback}
        except Exception:
            return {"summary": content}

    def summarize(self, text: str, **kwargs) -> dict:
        """Backwards-compatible helper used by tests and callers expecting `summarize`."""
        return self.call_llm(text, **kwargs)


_default = LLMClient()


def summarize(text: str) -> dict:
    # convenience wrapper using SummaryModel if available
    try:
        from .models import SummaryModel

        return _default.call_llm(text, response_model=SummaryModel)
    except Exception:
        return _default.call_llm(text)
