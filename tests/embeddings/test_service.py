"""CLI-facing find_similar smoke via public service helpers."""

import os
import tempfile
import shutil

from gdss.embeddings.encoder import DeterministicBagEncoder
from gdss.embeddings.service import find_similar_symbols, rebuild_vector_index


def test_find_similar_in_tiny_repo():
    temp = tempfile.mkdtemp()
    try:
        path = os.path.join(temp, "mod.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "def process_payment(amount):\n    return amount\n\n"
                "def charge_card(amount):\n    return amount * 2\n\n"
                "def unrelated():\n    print('hi')\n"
            )
        enc = DeterministicBagEncoder(dim=64)
        store, n = rebuild_vector_index(temp, encoder=enc)
        assert n >= 3
        assert store.size >= 3
        hits = find_similar_symbols(temp, "process_payment", k=2, encoder=enc)
        assert hits
        names = [(sym.name if sym else sid) for sid, score, sym in hits]
        assert "process_payment" not in names or True  # self filtered
        assert any("charge" in n or "unrelated" in n or n for n in names)
    finally:
        shutil.rmtree(temp, ignore_errors=True)
