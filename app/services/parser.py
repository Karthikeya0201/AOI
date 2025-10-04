from dataclasses import dataclass, field
from typing import Dict, List, Pattern
import re

@dataclass
class MarkingSpec:
    part_number: str
    regexes: List[Pattern]
    hints: List[str] = field(default_factory=list)


COMMON_FIELDS = [
    r"lot\s*[:#-]?\s*[a-z0-9\-]+",
    r"date\s*code\s*[:#-]?\s*[a-z0-9\-]+",
    r"yyww",
    r"yww",
    r"country\s*of\s*origin|made\s*in\s*[a-z]+",
]


def _escape_part(part_number: str) -> str:
    return re.escape(part_number).replace("\\ ", "\\s+")


def build_marking_spec_from_sections(part_number: str, sections: Dict[str, str]) -> MarkingSpec:
    tokens = [part_number]

    for url, text in sections.items():
        lower = text.lower()
        for key in ["marking", "top marking", "laser", "package", "pin 1"]:
            if key in lower:
                tokens.append(key)
        # Extract example lines with part number
        for m in re.finditer(re.escape(part_number.split()[0]), text, flags=re.I):
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 40)
            sample = text[start:end]
            tokens.append(sample)

    regexes: List[Pattern] = []

    # Base: the part number appears verbatim (allow whitespace/hyphen variants)
    pn_regex = _escape_part(part_number).replace("-", r"[-\s]?")
    regexes.append(re.compile(pn_regex, flags=re.I))

    # Common fields
    for cf in COMMON_FIELDS:
        try:
            regexes.append(re.compile(cf, flags=re.I))
        except re.error:
            continue

    # Variants around samples
    for t in tokens:
        t = re.sub(r"\s+", "\\s+", re.escape(t.strip()))
        if len(t) >= 6:
            try:
                regexes.append(re.compile(t, flags=re.I))
            except re.error:
                continue

    hints = list({"pn must be present", "check lot/date code"})
    return MarkingSpec(part_number=part_number, regexes=regexes, hints=hints)
