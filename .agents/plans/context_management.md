# Context Management & Semantic Batching Plan

This plan addresses the risk of exceeding the LLM's context window when dealing with massive codebase merges, ensuring the system remains reliable without truncating patches or losing semantic meaning.

## 1. Current Architecture Review

GDSS already processes conflicts efficiently in one regard: **it does not send all conflicts at once**. The orchestration in `gdss/ai/suggester.py` isolates each colliding `CodeSymbol` (e.g., a single function or class) and queries the LLM separately for each conflict and each resolution strategy. 

However, two major risks remain:
1. **Output Truncation:** `ollama_provider.py` hardcodes `max_tokens=1024`. If an LLM needs to rewrite a 150-line function, it will hit this limit, output a broken patch, and the validation layer will silently reject it.
2. **Input Overflow:** If a single colliding `CodeSymbol` (e.g., a massive God-class) is 10,000 lines long, sending the `anchored_block` will exceed the model's input context window, causing a crash or severe hallucination.

## 2. Proposed Changes

### Fix Output Truncation
#### [MODIFY] `gdss/ai/ollama_provider.py`
- Change the hardcoded `num_predict: max_tokens` (1024) to `num_predict: -1` to allow the local model to generate as much text as it needs up to its maximum context window.
- Increase the default `timeout` from `30.0` to `120.0` seconds to allow the model time to stream large patches.

### Protect Input Context (Context Window Manager)
#### [MODIFY] `gdss/ai/suggester.py`
- Implement a lightweight token estimator (e.g., `len(prompt) // 4` as a conservative heuristic).
- Define a strict `MAX_PROMPT_TOKENS` (e.g., `6000` for an 8k context model).
- Before calling `provider.complete()`, measure the prompt. If the prompt exceeds the threshold, trigger the **Semantic Fallback**.

## 3. Open Questions / User Review Required

> [!WARNING]
> **How should we handle a single conflict that is too massive for the context window?**
> 
> I need your decision on which **Semantic Fallback** strategy to implement:
> 
> **Option A: Graceful Bypass (Recommended for Safety)**
> If the anchor block exceeds the context window, the AI layer gracefully skips LLM patch generation for that specific conflict. It flags it as "Too large for AI resolution" and defers to human manual review. This guarantees zero semantic corruption.
> 
> **Option B: AST Condensation (High Risk)**
> We build a new module that uses `tree-sitter` to strip out the bodies of unmodified methods within the class, replacing them with `# ...`. The risk is that the LLM might literally output `# ...` in its patch, causing data loss when the patch is applied.

Please let me know which fallback strategy (A or B) you prefer, and I will proceed with execution!
