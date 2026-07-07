"""AST structural fingerprints and normalized Levenshtein edit distance."""

from __future__ import annotations

from typing import List, Sequence, Tuple


def levenshtein_distance(a: Sequence[str], b: Sequence[str]) -> int:
    """Classic Levenshtein distance over token sequences."""
    if a == b:
        return 0
    len_a = len(a)
    len_b = len(b)
    if len_a == 0:
        return len_b
    if len_b == 0:
        return len_a

    prev = list(range(len_b + 1))
    for i, token_a in enumerate(a, start=1):
        curr = [i]
        for j, token_b in enumerate(b, start=1):
            insert_cost = curr[j - 1] + 1
            delete_cost = prev[j] + 1
            replace_cost = prev[j - 1] + (0 if token_a == token_b else 1)
            curr.append(min(insert_cost, delete_cost, replace_cost))
        prev = curr
    return prev[-1]


def normalized_similarity(tokens_a: Sequence[str], tokens_b: Sequence[str]) -> float:
    """
    Normalized structural similarity in [0, 1]:
    1 - distance / max(len(a), len(b))
    """
    if not tokens_a and not tokens_b:
        return 1.0
    max_len = max(len(tokens_a), len(tokens_b))
    if max_len == 0:
        return 1.0
    distance = levenshtein_distance(tokens_a, tokens_b)
    return 1.0 - (distance / max_len)


def fingerprint_bucket(tokens: Sequence[str], prefix_len: int = 4) -> str:
    """Hash bucket key for candidate pre-filtering during rename detection."""
    if not tokens:
        return ""
    head = tokens[:prefix_len]
    return "|".join(head)


def extract_tokens_from_body_text(body: str) -> List[str]:
    """
    Fallback token extractor when AST tokens are unavailable.
    Maps common Python/JS statement keywords to structural tokens.
    """
    tokens: List[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if line.startswith("if "):
            tokens.append("if_statement")
        elif line.startswith("elif "):
            tokens.append("elif_clause")
        elif line.startswith("else:"):
            tokens.append("else_clause")
        elif line.startswith("for "):
            tokens.append("for_statement")
        elif line.startswith("while "):
            tokens.append("while_statement")
        elif line.startswith("try:"):
            tokens.append("try_statement")
        elif line.startswith("except"):
            tokens.append("except_clause")
        elif line.startswith("return "):
            tokens.append("return_statement")
        elif line.startswith("def ") or line.startswith("function "):
            tokens.append("function_definition")
        elif line.startswith("class "):
            tokens.append("class_definition")
        elif "=" in line:
            tokens.append("assignment")
        else:
            tokens.append("expression_statement")
    return tokens
