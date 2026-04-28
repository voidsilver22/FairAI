from __future__ import annotations

import importlib.util
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

import pandas as pd


EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_PATTERN = re.compile(r"\+?\d[\d\-\s]{8,}\d")
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.I)
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
PRONOUN_PATTERN = re.compile(
    r"\b(?:he|she|him|her|his|hers|mr|mrs|ms)\b",
    re.I,
)

PROXY_PATTERNS: dict[str, re.Pattern[str]] = {
    "gender_proxy": re.compile(
        r"\b(?:women(?:'s)?|female|girl(?:s)?|maternity|sorority|brotherhood|fraternity)\b",
        re.I,
    ),
    "ethnicity_proxy": re.compile(
        r"\b(?:hispanic|latino|latina|african american|black student union|asian american|native american|minority)\b",
        re.I,
    ),
    "prestige_proxy": re.compile(
        r"\b(?:ivy league|harvard|stanford|mit|princeton|wellesley|spelman|howard|smith college)\b",
        re.I,
    ),
    "location_proxy": re.compile(
        r"\b(?:zip code|postcode|brooklyn|bronx|queens|oakland|detroit|atlanta)\b",
        re.I,
    ),
    "affinity_proxy": re.compile(
        r"\b(?:society of hispanic professional engineers|nsbe|women in tech|cultural club|diversity council)\b",
        re.I,
    ),
}


@dataclass(slots=True)
class ScrubResult:
    frame: pd.DataFrame
    summary: dict[str, Any]


class ResumeScrubber:
    """Mask direct and proxy identifiers from resume text."""

    def __init__(self) -> None:
        self._spacy_nlp = self._load_spacy_model()

    def scrub_frame(self, frame: pd.DataFrame, text_column: str) -> ScrubResult:
        scrubbed_texts: list[str] = []
        mask_counts: list[int] = []
        proxy_counts: list[int] = []
        proxy_categories: list[str] = []
        aggregate_counter: Counter[str] = Counter()

        for text in frame[text_column].fillna("").astype(str).tolist():
            scrubbed_text, details = self.scrub_text(text)
            scrubbed_texts.append(scrubbed_text)
            mask_counts.append(details["mask_count"])
            proxy_counts.append(details["proxy_hit_count"])
            proxy_categories.append(",".join(details["proxy_categories"]))
            aggregate_counter.update(details["proxy_categories"])

        scrubbed = frame.copy()
        scrubbed["__scrubbed_text"] = scrubbed_texts
        scrubbed["__mask_count"] = mask_counts
        scrubbed["__proxy_hit_count"] = proxy_counts
        scrubbed["__proxy_categories"] = proxy_categories

        return ScrubResult(
            frame=scrubbed,
            summary={
                "total_masks": int(sum(mask_counts)),
                "total_proxy_hits": int(sum(proxy_counts)),
                "proxy_categories": dict(aggregate_counter),
            },
        )

    def scrub_text(self, text: str) -> tuple[str, dict[str, Any]]:
        working = text
        mask_count = 0
        categories: list[str] = []

        direct_patterns = (
            (EMAIL_PATTERN, "[EMAIL]"),
            (PHONE_PATTERN, "[PHONE]"),
            (URL_PATTERN, "[URL]"),
            (YEAR_PATTERN, "[DATE]"),
            (PRONOUN_PATTERN, "[PRONOUN]"),
        )

        for pattern, replacement in direct_patterns:
            matches = pattern.findall(working)
            if matches:
                mask_count += len(matches)
                working = pattern.sub(replacement, working)

        if self._spacy_nlp is not None and working.strip():
            doc = self._spacy_nlp(working)
            replacements: list[tuple[int, int, str]] = []
            for entity in doc.ents:
                if entity.label_ == "PERSON":
                    replacements.append((entity.start_char, entity.end_char, "[PERSON]"))
            if replacements:
                rebuilt: list[str] = []
                cursor = 0
                for start, end, replacement in replacements:
                    rebuilt.append(working[cursor:start])
                    rebuilt.append(replacement)
                    cursor = end
                    mask_count += 1
                rebuilt.append(working[cursor:])
                working = "".join(rebuilt)

        for category, pattern in PROXY_PATTERNS.items():
            matches = pattern.findall(working)
            if matches:
                categories.extend([category] * len(matches))
                working = pattern.sub(f"[{category.upper()}]", working)

        return working, {
            "mask_count": mask_count,
            "proxy_hit_count": len(categories),
            "proxy_categories": sorted(set(categories)),
        }

    def _load_spacy_model(self) -> Any | None:
        if importlib.util.find_spec("spacy") is None:
            return None
        try:
            import spacy

            try:
                return spacy.load("en_core_web_sm")
            except Exception:
                return spacy.blank("en")
        except Exception:
            return None

