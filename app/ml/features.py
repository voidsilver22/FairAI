from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd


TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+#\-.]{1,}")
YEARS_PATTERN = re.compile(r"(\d{1,2})\+?\s+years?", re.I)

SKILL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "python": ("python", "pandas", "fastapi"),
    "java": ("java", "spring"),
    "sql": ("sql", "postgres", "mysql"),
    "cloud": ("gcp", "aws", "azure", "cloud run", "vertex"),
    "ml": ("machine learning", "pytorch", "tensorflow", "sklearn"),
    "data": ("analytics", "etl", "warehouse", "pipeline"),
    "leadership": ("lead", "manager", "mentored", "ownership"),
    "security": ("security", "compliance", "gdpr", "soc2"),
}

EDUCATION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "bachelor": ("bachelor", "b.sc", "bs", "btech"),
    "master": ("master", "m.sc", "ms", "mtech", "mba"),
    "doctorate": ("phd", "doctorate"),
}


@dataclass(slots=True)
class FeatureExtractionResult:
    features: pd.DataFrame
    annotated_frame: pd.DataFrame


class FeatureExtractor:
    """Deterministic feature extraction with optional semantic hash features."""

    def __init__(self, hash_dimensions: int = 16) -> None:
        self.hash_dimensions = hash_dimensions

    def build_features(
        self,
        frame: pd.DataFrame,
        *,
        text_column: str,
        label_column: str,
        protected_attributes: list[str],
        include_protected_attributes: bool,
    ) -> FeatureExtractionResult:
        annotated = frame.copy()
        feature_rows: list[dict[str, float]] = []

        for text, mask_count, proxy_count in zip(
            annotated[text_column].fillna("").astype(str).tolist(),
            annotated.get("__mask_count", pd.Series([0] * len(annotated))).tolist(),
            annotated.get("__proxy_hit_count", pd.Series([0] * len(annotated))).tolist(),
            strict=False,
        ):
            feature_rows.append(
                self._extract_text_features(
                    text=text,
                    mask_count=float(mask_count),
                    proxy_count=float(proxy_count),
                )
            )

        text_features = pd.DataFrame(feature_rows, index=annotated.index)
        annotated["years_experience_bucket"] = pd.cut(
            text_features["years_experience"],
            bins=[-1, 2, 5, 10, 40],
            labels=["0-2", "3-5", "6-10", "10+"],
        ).astype(str)
        annotated["resume_length_bucket"] = pd.cut(
            text_features["token_count"],
            bins=[-1, 120, 250, 500, 5000],
            labels=["short", "medium", "long", "very_long"],
        ).astype(str)
        annotated["education_level_bucket"] = pd.cut(
            text_features["education_level"],
            bins=[-1, 1, 2, 3],
            labels=["none_or_other", "bachelor", "master_plus"],
        ).astype(str)

        numeric_columns = [
            column
            for column in annotated.columns
            if column not in {label_column, "__label", text_column, "__resume_text", "__scrubbed_text"}
            and column not in protected_attributes
            and pd.api.types.is_numeric_dtype(annotated[column])
        ]
        numeric_features = annotated[numeric_columns].copy() if numeric_columns else pd.DataFrame(index=annotated.index)

        categorical_columns = [
            column
            for column in annotated.columns
            if column not in {label_column, "__label", text_column, "__resume_text", "__scrubbed_text"}
            and column not in protected_attributes
            and column not in numeric_columns
            and annotated[column].dtype == object
            and annotated[column].nunique(dropna=True) <= 8
        ]
        categorical_features = (
            pd.get_dummies(
                annotated[categorical_columns].fillna("unknown"),
                prefix=categorical_columns,
                dtype=float,
            )
            if categorical_columns
            else pd.DataFrame(index=annotated.index)
        )

        protected_features = (
            pd.get_dummies(
                annotated[protected_attributes].fillna("unknown"),
                prefix=protected_attributes,
                dtype=float,
            )
            if include_protected_attributes
            else pd.DataFrame(index=annotated.index)
        )

        feature_frame = pd.concat(
            [text_features, numeric_features, categorical_features, protected_features],
            axis=1,
        ).fillna(0.0)

        if feature_frame.empty:
            feature_frame = pd.DataFrame({"constant_feature": np.ones(len(annotated))})

        return FeatureExtractionResult(
            features=feature_frame.astype(float),
            annotated_frame=annotated,
        )

    def _extract_text_features(
        self,
        *,
        text: str,
        mask_count: float,
        proxy_count: float,
    ) -> dict[str, float]:
        tokens = TOKEN_PATTERN.findall(text.lower())
        joined = " ".join(tokens)
        years = [
            int(match)
            for match in YEARS_PATTERN.findall(text)
            if match.isdigit()
        ]

        features: dict[str, float] = {
            "token_count": float(len(tokens)),
            "unique_token_ratio": float(len(set(tokens)) / max(len(tokens), 1)),
            "years_experience": float(max(years) if years else 0),
            "mask_count": mask_count,
            "proxy_count": proxy_count,
            "certification_mentions": float(joined.count("certif")),
            "project_mentions": float(joined.count("project")),
            "leadership_mentions": float(
                sum(joined.count(keyword) for keyword in ("lead", "manager", "mentored"))
            ),
            "education_level": 0.0,
        }

        for skill_name, keywords in SKILL_KEYWORDS.items():
            features[f"skill_{skill_name}"] = float(
                sum(joined.count(keyword) for keyword in keywords)
            )

        education_level = 0.0
        for bucket, keywords in EDUCATION_KEYWORDS.items():
            if any(keyword in joined for keyword in keywords):
                if bucket == "bachelor":
                    education_level = max(education_level, 1.0)
                elif bucket == "master":
                    education_level = max(education_level, 2.0)
                elif bucket == "doctorate":
                    education_level = max(education_level, 3.0)
        features["education_level"] = education_level

        for bucket_index in range(self.hash_dimensions):
            features[f"hash_feature_{bucket_index}"] = 0.0

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
            bucket = int(digest[:8], 16) % self.hash_dimensions
            features[f"hash_feature_{bucket}"] += 1.0

        total_tokens = max(len(tokens), 1)
        for bucket_index in range(self.hash_dimensions):
            features[f"hash_feature_{bucket_index}"] = round(
                features[f"hash_feature_{bucket_index}"] / total_tokens,
                6,
            )

        return features

