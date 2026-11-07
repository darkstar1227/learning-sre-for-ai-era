"""
Validation utilities for AI Change Manifests.
Corresponds to Day28.md section ③ (驗收 checklist).
"""

import yaml
from pathlib import Path
from typing import Dict, Tuple
from pydantic import ValidationError
from app.schemas import ChangeManifest


def validate_manifest_yaml(file_path: str | Path) -> Tuple[bool, ChangeManifest | None, list[str]]:
    """
    Load and validate a YAML change manifest.

    Args:
        file_path: Path to YAML manifest file

    Returns:
        (success: bool, manifest: ChangeManifest or None, errors: list of error messages)
    """
    errors = []

    # Check file exists
    path = Path(file_path)
    if not path.exists():
        return False, None, [f"File not found: {file_path}"]

    # Load YAML
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if data is None:
            return False, None, ["YAML file is empty"]
    except yaml.YAMLError as e:
        return False, None, [f"YAML parsing error: {str(e)}"]
    except Exception as e:
        return False, None, [f"Error reading file: {str(e)}"]

    # Validate against schema
    try:
        manifest = ChangeManifest(**data)
        return True, manifest, []
    except ValidationError as e:
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            errors.append(f"{loc}: {error['msg']}")
        return False, None, errors


def validate_manifest_dict(data: dict) -> Tuple[bool, ChangeManifest | None, list[str]]:
    """
    Validate a manifest from a dictionary.

    Args:
        data: Dictionary with manifest fields

    Returns:
        (success: bool, manifest: ChangeManifest or None, errors: list of error messages)
    """
    try:
        manifest = ChangeManifest(**data)
        return True, manifest, []
    except ValidationError as e:
        errors = []
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            errors.append(f"{loc}: {error['msg']}")
        return False, None, errors


def check_manifest_requirements(manifest: ChangeManifest) -> Dict[str, bool]:
    """
    Check if manifest meets Day28 verification checklist.
    Corresponds to Day28.md section ③ (驗收).

    Returns:
        Dictionary of requirement checks
    """
    return {
        # Requirement 1: "code 以外的 AI artefact 也有版本"
        "ai_artifacts_versioned": (
            manifest.prompt_version != "TODO"
            and manifest.model != "TODO"
            and manifest.golden_dataset != "TODO"
        ),

        # Requirement 2: "pipeline 含 evaluation 與 release 後觀測"
        "has_evaluation_gate": manifest.release_gate is not None,
        "has_observation_plan": (
            manifest.observation_metrics is not None
            and len(manifest.observation_metrics) > 0
        ),

        # Requirement 3: "rollback 有 owner 與相容性考量"
        "has_owner": manifest.owner is not None,
        "has_rollback_reference": manifest.rollback is not None,
        "has_compatibility_notes": manifest.compatibility_notes is not None,
    }


def generate_manifest_template(override: dict = None) -> dict:
    """
    Generate a sample manifest template for documentation.
    Corresponds to Day28.md section ③ (example YAML).

    Args:
        override: Optional dictionary to override default values

    Returns:
        Template manifest dictionary
    """
    template = {
        "change_id": "answer-v17",
        "code_revision": "abc123def456",
        "prompt_version": "2026-09-21-a",
        "model": "google/gemini-3.6-flash",
        "golden_dataset": "v3",
        "retrieval_index_version": None,
        "tool_schema_version": None,
        "evaluator_version": None,
        "release_gate": "citation_valid_and_safety_checks",
        "rollback": "answer-v16",
        "owner": "team-name",
        "observation_metrics": [
            "citation_accuracy",
            "safety_blocks",
            "response_latency_p95",
        ],
        "compatibility_notes": "New tool schema requires handler update before rollback",
    }

    if override:
        template.update(override)

    return template
