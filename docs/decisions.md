# Decisions

Architectural and tooling choices worth preserving beyond the user stories. New entries are appended with a short date or milestone when helpful.

## OpenAI-compatible LLM providers

**Context:** Agents need a single integration pattern for self-hosted and vendor APIs.

**Decision:** Treat every configured `LLMProvider` as an **OpenAI-compatible HTTP API** (chat and model listing). Discovery uses the standard client against the provider base URL (including `/v1` as appropriate).

**Consequences:** URLs and model identifiers must match what each server exposes. Providers are not special-cased per vendor in application code.

## Local default inference (development)

**Context:** Milestone 0 aims for local-first development without mandatory cloud keys or Admin setup for the common path.

**Decision:** Bundle **llama.cpp `llama-server`** (installed via **mise**), start it alongside the dev stack (**process-compose**), and use **`OpenAIProvider`** in application code for the fallback path. Weights are fetched during **`mise run init`** (see `scripts/download_local_llm.sh`; default GGUF is a pinned community quant).

**Consequences:** Dev machines need sufficient disk and RAM for the chosen GGUF. Fallback defaults are controlled via Django settings / env (`LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`, etc.).

## llama-server model names

**Context:** Clients send an OpenAI-style `model` field; the server must agree on valid values.

**Decision:** Start **`llama-server`** with **`-a` / `--alias`** so the advertised model id is stable (e.g. `gemma-2-2b-it`) and matches **`LOCAL_LLM_MODEL`**.

**Alternatives considered:** Relying on the default id derived from the GGUF filename (no `--alias`) — predictable but verbose and tied to the file name.

**Reference:** [llama-server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) (`--alias` controls API-visible model names; without it, the loaded file name is typically used).
