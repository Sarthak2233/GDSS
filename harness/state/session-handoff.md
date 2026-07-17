# Session Handoff: Phase 2 Embeddings Complete

## Current State
`phase2-embeddings` is **done**. Probabilistic brain Layer 6 is live and assistive only:

- `gdss/embeddings/` — bag encoder (default), optional ONNX MiniLM, cosine, branch tips
- FAISS (or numpy fallback) index under `.gdss/vectors/`
- CLI: `gdss similar <symbol>`, `gdss reindex`
- Deterministic brain does **not** import embeddings
- `bash harness/verify.sh` ALL LAYERS GREEN (55 pytest)

## Next Steps
1. **`phase3-drift`** — continuous drift engine I(B_i), alerts, daemon (depends on embeddings)
2. Optional: ship real MiniLM ONNX under `.gdss/models/` + `GDSS_EMBEDDING_BACKEND=onnx`
3. Optional later: Qdrant for multi-repo SaaS (not required for local CLI)

## How to resume
```bash
bash harness/init.sh
source venv/bin/activate  # if using project venv
pip install -e ".[embeddings]"  # faiss-cpu + onnxruntime
bash harness/verify.sh
gdss similar process_payment --repo . -k 5
```
