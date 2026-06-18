"""LLM access: Ollama embeddings + provider-aware summarization.

Embeddings always run locally via Ollama (nomic-embed-text).

Summarization provider is inferred from the model name:
  - a name containing "deepseek-v4" -> DeepSeek API (needs DEEPSEEK_API_KEY)
  - anything else                   -> local Ollama model

This keeps the system local-first while leaving a one-line switch to the
DeepSeek API once a key is available.
"""

import os

import requests

# Prompt is locked per the handoff — do not edit without escalation.
SUMMARIZE_PROMPT = """You are indexing an AI conversation for later retrieval.
Write exactly 3 sentences summarizing what was discussed and what was resolved or built.
Then list 5-8 topic keywords as a comma-separated line prefixed with "Keywords:".
Be specific: include tool names, file paths, model names, and technical terms.
Do not use vague phrases like "various topics" or "several issues."

Conversation:
{messages}"""

# Cap chunk text fed to the summarizer to keep latency and context bounded.
_MAX_CHUNK_CHARS = 8000


def ollama_embed(text: str, model: str, host: str) -> list[float]:
    """Return an embedding vector for `text` from a local Ollama model."""
    resp = requests.post(
        f"{host.rstrip('/')}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    embedding = data.get("embedding")
    if not embedding:
        raise RuntimeError(f"Empty embedding from Ollama for model {model!r}")
    return embedding


def _ollama_generate(prompt: str, model: str, host: str) -> str:
    resp = requests.post(
        f"{host.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 8192, "temperature": 0.2},
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def _deepseek_generate(prompt: str, model: str, base_url: str) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "summarize_model requests DeepSeek but DEEPSEEK_API_KEY is not set."
        )
    resp = requests.post(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "stream": False,
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def generate(
    prompt: str,
    model: str,
    ollama_host: str,
    deepseek_base_url: str = "https://api.deepseek.com",
) -> str:
    """Provider-aware text generation (summarization, distillation, etc.)."""
    if "deepseek-v4" in model:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if api_key:
            return _deepseek_generate(prompt, model, deepseek_base_url)
        # No API key — fall back to local Ollama using the same model slot name
        # is wrong; caller should pass a local model in config when no key exists.
        model = os.environ.get("CONVMEM_FALLBACK_MODEL", "llama3.1:8b")
    return _ollama_generate(prompt, model, ollama_host)


def summarize(
    chunk_text: str,
    model: str,
    ollama_host: str,
    deepseek_base_url: str = "https://api.deepseek.com",
) -> str:
    """Summarize a conversation chunk into 3 sentences + a Keywords line."""
    if len(chunk_text) > _MAX_CHUNK_CHARS:
        chunk_text = chunk_text[:_MAX_CHUNK_CHARS]
    prompt = SUMMARIZE_PROMPT.format(messages=chunk_text)

    if "deepseek-v4" in model and os.environ.get("DEEPSEEK_API_KEY"):
        return _deepseek_generate(prompt, model, deepseek_base_url)
    if "deepseek-v4" in model:
        model = "llama3.1:8b"
    return _ollama_generate(prompt, model, ollama_host)
