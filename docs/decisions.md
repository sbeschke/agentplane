# Decisions

Architectural and tooling choices worth preserving beyond the user stories. New entries are appended with a short date or milestone when helpful.

## OpenAI-compatible LLM providers

**Context:** Agents need a single integration pattern for self-hosted and vendor APIs.

**Decision:** Treat every configured `LLMProvider` as an **OpenAI-compatible HTTP API** (chat and model listing). Discovery uses the standard client against the provider base URL (including `/v1` as appropriate).

**Consequences:** URLs and model identifiers must match what each server exposes. Providers are not special-cased per vendor in application code.

## Local default inference (development)

**Context:** Milestone 0 aims for local-first development without mandatory cloud keys or Admin setup for the common path.

**Decision:** Ship **`llama-server`** from official **ggml-org/llama.cpp** release assets (downloaded by **`scripts/download_llama_runtime.sh`**, pinned build **`LLAMA_CPP_BUILD`** / default `9090`), not the CPU-only archive that generic installers often pick. Start it via **`scripts/run-local-llm.sh`** with **`-ngl auto`** so layers offload to GPU when a backend is present. Use **`OpenAIProvider`** in application code for the fallback path. GGUF weights are fetched during **`mise run init`** (`scripts/download_local_llm.sh`).

**GPU / backends:** Upstream does not publish a Linux x86_64 **CUDA** tarball; **Vulkan** is used on Linux x86_64 (`ubuntu-vulkan-x64`). **macOS arm64** builds include **Metal**. **Linux arm64** uses the generic `ubuntu-arm64` asset (typically CPU). NVIDIA on Linux relies on a working Vulkan driver/runtime.

**Consequences:** Dev machines need sufficient disk and RAM for the GGUF and runtime. Fallback defaults use Django settings / env (`LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`, etc.); the server binary honors the same names via `run-local-llm.sh` (e.g. `LOCAL_LLM_PORT`, `LOCAL_LLM_GGUF`).

## llama-server model names

**Context:** Clients send an OpenAI-style `model` field; the server must agree on valid values.

**Decision:** Start **`llama-server`** with **`-a` / `--alias`** so the advertised model id is stable (e.g. `gemma-2-2b-it`) and matches **`LOCAL_LLM_MODEL`**.

**Alternatives considered:** Relying on the default id derived from the GGUF filename (no `--alias`) — predictable but verbose and tied to the file name.

**Reference:** [llama-server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) (`--alias` controls API-visible model names; without it, the loaded file name is typically used).
