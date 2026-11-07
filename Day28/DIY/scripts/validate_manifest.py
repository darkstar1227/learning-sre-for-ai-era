"""
Script to validate change manifests.
Corresponds to Day28.md section ③ (寫 change manifest) and verification checklist.
"""

import sys
import json
from pathlib import Path
from app.validator import (
    validate_manifest_yaml,
    validate_manifest_dict,
    check_manifest_requirements,
)
from app.schemas import ChangeManifest


def validate_single_file(file_path: str) -> int:
    """
    Validate a single manifest YAML file.

    Returns:
        0 if valid, 1 if invalid
    """
    print(f"\n{'='*60}")
    print(f"Validating: {file_path}")
    print('='*60)

    success, manifest, errors = validate_manifest_yaml(file_path)

    if not success:
        print("❌ Validation FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("✓ YAML schema validation PASSED")
    print(f"  Change ID: {manifest.change_id}")
    print(f"  Model: {manifest.model}")
    print(f"  Prompt Version: {manifest.prompt_version}")
    print(f"  Owner: {manifest.owner}")

    # Check Day28 verification checklist
    print("\n📋 Day28 Verification Checklist:")
    requirements = check_manifest_requirements(manifest)

    checklist = [
        ("code 以外的 AI artefact 也有版本", "ai_artifacts_versioned"),
        ("pipeline 含 evaluation 環節", "has_evaluation_gate"),
        ("pipeline 含 release 後觀測", "has_observation_plan"),
        ("rollback 有 owner", "has_owner"),
        ("rollback 有參考版本", "has_rollback_reference"),
        ("rollback 有相容性考量", "has_compatibility_notes"),
    ]

    all_passed = True
    for description, key in checklist:
        status = "✓" if requirements[key] else "✗"
        print(f"  {status} {description}")
        if not requirements[key]:
            all_passed = False

    if all_passed:
        print("\n✓✓✓ All requirements met!")
        return 0
    else:
        print("\n⚠️  Some requirements not met (but schema is valid)")
        return 1


def validate_manifest_inline(data: dict) -> tuple[bool, ChangeManifest | None]:
    """
    Validate a manifest from inline dictionary (for testing).

    Returns:
        (success, manifest or None)
    """
    success, manifest, errors = validate_manifest_dict(data)
    if not success:
        print("Validation failed:")
        for error in errors:
            print(f"  - {error}")
    return success, manifest


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_manifest.py <manifest.yaml>")
        print("\nExample:")
        print("  python scripts/validate_manifest.py manifests/answer-v17.yaml")
        sys.exit(1)

    file_path = sys.argv[1]
    result = validate_single_file(file_path)
    sys.exit(result)


if __name__ == "__main__":
    main()
