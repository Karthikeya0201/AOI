from dataclasses import dataclass
from typing import List
from rapidfuzz import fuzz

@dataclass
class ComparisonDetail:
    pattern: str
    matched: bool
    score: float

@dataclass
class ComparisonResult:
    is_genuine: bool
    confidence: float
    details: List[ComparisonDetail]


def compare_marking_to_spec(text: str, spec) -> ComparisonResult:
    normalized = " ".join(text.split())

    details: List[ComparisonDetail] = []
    scores: List[float] = []

    for r in spec.regexes:
        pattern = r.pattern
        if r.search(normalized):
            score = 1.0
            matched = True
        else:
            # fuzzy ratio vs pattern text as heuristic
            score = fuzz.partial_ratio(normalized.lower(), pattern.lower()) / 100.0
            matched = score > 0.6
        details.append(ComparisonDetail(pattern=pattern, matched=matched, score=score))
        scores.append(score)

    # Require strong presence of part number and at least one common field
    pn_ok = max(scores[:1]) if scores else 0.0
    fields_ok = 1.0 if any(d.matched for d in details[1:]) else 0.0

    confidence = min(1.0, 0.6 * pn_ok + 0.4 * (sum(scores) / max(1, len(scores))))
    is_genuine = pn_ok > 0.9 and fields_ok > 0.0 and confidence > 0.7

    return ComparisonResult(is_genuine=is_genuine, confidence=confidence, details=details)
