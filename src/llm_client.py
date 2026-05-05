import json
import re
import time
from typing import Optional, Any, Type

import httpx

from .config import cfg, logger


class LLMClient:
    def __init__(self, endpoint: str = None, api_key: str = None, timeout: Optional[int] = None):
        self.endpoint = endpoint or cfg.LLAMA_ENDPOINT
        self.api_key = api_key or cfg.LLAMA_API_KEY
        self.timeout = timeout or int(getattr(cfg, "LLM_TIMEOUT", 120))
        self.client = httpx.Client(timeout=self.timeout)

    def call_llm(self, text: str, response_model: Optional[Type[Any]] = None, max_tokens: int = 20480, max_retries: int = 1) -> dict:
        """Call the LLM and optionally validate/parse the JSON output."""
        url = f"{self.endpoint}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        system_msg = (
            "You are a highly selective technical summarization assistant. Respond in Japanese.\n"
            "Assess if the article is TRULY useful for an advanced student who has mastered Python basics and has been learning/using it for 3 years.\n"
            "STRICT CRITERIA:\n"
            "- IGNORE basic tutorials, introductory guides, and common library updates.\n"
            "- IGNORE general AI hype or surface-level news.\n"
            "- ONLY ACCEPT: Advanced architectural patterns, deep performance optimizations, cutting-edge LLM/ML implementation details, or significant industry shifts that require seasoned expertise to appreciate.\n"
            "- A 'useful' article must have technical depth or high practical value for an experienced developer.\n"
            "- IF IMPORTANCE IS LESS THAN 4, is_useful_for_python_student MUST BE false.\n"
            "\n"
            "Produce a JSON object with EXACTLY these keys:\n"
            "{\n"
            "  \"summary\": \"string\",\n"
            "  \"highlights\": [\"string\", ...],\n"
            "  \"importance\": 1-5,\n"
            "  \"is_useful_for_python_student\": true/false,\n"
            "  \"reason_for_usefulness\": \"string\"\n"
            "}\n"
            "Do not skip any keys. Put the JSON inside a ```json code block."
        )
        user_msg = "Article:\n```" + text + "```"
        
        max_input_chars = 4000
        if len(text) > max_input_chars:
            text = text[:max_input_chars]
            user_msg = "Article (Truncated):\n```" + text + "```"

        logger.info(f"[LLM] Request starting. Text length: {len(text)} chars.")
        logger.debug(f"[LLM] System Prompt: {system_msg}")
        logger.debug(f"[LLM] User Prompt: {user_msg}")

        
        start_time = time.time()
        attempt = 0
        last_err = None
        while attempt <= max_retries:
            try:
                payload = {
                    "model": cfg.LLAMA_MODEL,
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
                logger.warning(f"[LLM] Attempt {attempt} failed: {e}")
                continue
        
        duration = time.time() - start_time
        if last_err:
            logger.error(f"[LLM] Failed after {duration:.2f}s: {last_err}")
            return {"summary": "", "error": str(last_err)}

        try:
            msg = data["choices"][0]["message"]
            content = msg.get("content") or ""
            logger.info(f"[LLM] Response received in {duration:.2f}s. Content length: {len(content)}")
            clean_content = content[:200].replace('\n', ' ')
            logger.info(f"[LLM] Raw Content (first 200 chars): {clean_content}...")
            logger.debug(f"[LLM] Full Raw Content: {content}")
        except Exception as e:
            logger.error(f"[LLM] Failed to parse response data: {e}")
            content = json.dumps(data)

        def _extract_json_from_text(text: str):
            if not text:
                return None
            text = text.strip()
            
            # 1. Try to find content within ```json ... ``` blocks
            json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except Exception:
                    pass

            # 2. Try to find the last occurrence of { ... }
            # Models often put the summary at the very end.
            try:
                # Find all potential JSON objects
                starts = [m.start() for m in re.finditer(r"\{", text)]
                for start in reversed(starts):
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
            except Exception:
                pass

            # 3. Fallback to direct parse
            try:
                return json.loads(text)
            except Exception:
                pass

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

    def evaluate_title_fast(self, title: str) -> bool:
        """Fast filter to judge if article might be useful based on title only."""
        url = f"{self.endpoint}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        system_msg = (
            "You are a highly selective technical assistant. Respond ONLY with a JSON object.\n"
            "Assess if the following article title is LIKELY useful for an advanced student who has mastered Python basics and has been learning/using it for 3 years.\n"
            "STRICT CRITERIA:\n"
            "- IGNORE basic tutorials, introductory guides, and common library updates.\n"
            "- IGNORE general AI hype or surface-level news.\n"
            "- ONLY ACCEPT: Advanced architectural patterns, deep performance optimizations, cutting-edge LLM/ML implementation details, or significant industry shifts.\n"
            "Produce a JSON object with EXACTLY this key:\n"
            "{\n"
            "  \"is_useful\": true/false\n"
            "}\n"
            "Do not output anything else."
        )
        user_msg = f"Title: {title}"
        
        logger.info(f"[LLM] Title evaluation starting: {title}")
        start_time = time.time()
        try:
            payload = {
                "model": cfg.LLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                "max_tokens": 128,
            }
            resp = self.client.post(url, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"].get("content") or ""
            logger.info(f"[LLM] Title evaluation response ({time.time() - start_time:.2f}s): {content}")
            json_match = re.search(r"\{.*?\}", content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                return parsed.get("is_useful", False)
            return True # Fallback
        except Exception as e:
            logger.warning(f"[LLM] evaluate_title_fast failed for '{title}': {e}")
            return True

_default = LLMClient()


def evaluate_title(title: str) -> bool:
    return _default.evaluate_title_fast(title)

def summarize(text: str) -> dict:
    # convenience wrapper using SummaryModel if available
    try:
        from .models import SummaryModel

        return _default.call_llm(text, response_model=SummaryModel)
    except Exception:
        return _default.call_llm(text)
