"""
Demo script to show manifest validation in action.
Tests both valid and invalid manifests.
Corresponds to Day28.md section ③ (驗收).
"""

from pathlib import Path
from app.validator import (
    validate_manifest_yaml,
    check_manifest_requirements,
    generate_manifest_template,
)
from app.schemas import ChangeManifest


def demo_valid_manifests():
    """Demo 1: Validate correct manifests."""
    print("\n" + "="*70)
    print("DEMO 1: Validating well-formed manifests")
    print("="*70)

    manifest_files = [
        "manifests/answer-v17.yaml",
        "manifests/answer-v16.yaml",
    ]

    for file_path in manifest_files:
        path = Path(file_path)
        if not path.exists():
            print(f"\n⚠️  {file_path} not found (expected in DIY dir)")
            continue

        success, manifest, errors = validate_manifest_yaml(file_path)

        print(f"\n📄 {file_path}")
        if success:
            print("  ✓ Schema validation PASSED")
            print(f"    - change_id: {manifest.change_id}")
            print(f"    - model: {manifest.model}")
            print(f"    - owner: {manifest.owner}")

            # Show checklist
            reqs = check_manifest_requirements(manifest)
            print(f"    - requirements met: {sum(reqs.values())}/{len(reqs)}")
        else:
            print("  ✗ Validation FAILED")
            for error in errors:
                print(f"    - {error}")


def demo_invalid_manifests():
    """Demo 2: Show how invalid manifests are caught."""
    print("\n" + "="*70)
    print("DEMO 2: Invalid manifest examples")
    print("="*70)

    invalid_examples = [
        (
            "Missing required fields",
            {
                "change_id": "test-v1",
                # Missing: prompt_version, model, golden_dataset, etc.
            },
        ),
        (
            "Invalid model format",
            {
                "change_id": "test-v2",
                "prompt_version": "2026-09-21",
                "model": "invalid-format-no-slash",  # Should be "provider/name"
                "golden_dataset": "v1",
                "release_gate": "test",
                "owner": "team",
            },
        ),
        (
            "Empty change_id",
            {
                "change_id": "",
                "prompt_version": "2026-09-21",
                "model": "google/gemini",
                "golden_dataset": "v1",
                "release_gate": "test",
                "owner": "team",
            },
        ),
    ]

    from app.validator import validate_manifest_dict

    for description, invalid_data in invalid_examples:
        print(f"\n❌ {description}")
        success, manifest, errors = validate_manifest_dict(invalid_data)
        if not success:
            for error in errors:
                print(f"   └─ {error}")
        else:
            print("   ⚠️  Unexpectedly passed validation!")


def demo_template():
    """Demo 3: Show template generation."""
    print("\n" + "="*70)
    print("DEMO 3: Manifest template")
    print("="*70)

    template = generate_manifest_template()
    print("\nTemplate fields:")
    for key, value in template.items():
        if isinstance(value, list):
            print(f"  {key}:")
            for item in value:
                print(f"    - {item}")
        else:
            print(f"  {key}: {value}")


def demo_requirements_check():
    """Demo 4: Show Day28 verification checklist."""
    print("\n" + "="*70)
    print("DEMO 4: Day28 Verification Checklist")
    print("="*70)

    # Create a manifest that meets all requirements
    manifest = ChangeManifest(
        change_id="demo-v1",
        prompt_version="2026-09-21",
        model="google/gemini-3.6-flash",
        golden_dataset="v3",
        release_gate="citation_valid_and_safety_checks",
        rollback="demo-v0",
        owner="demo-team",
        observation_metrics=["accuracy", "latency"],
        compatibility_notes="Safe to rollback to v0",
    )

    reqs = check_manifest_requirements(manifest)

    print("\n✓ Manifest meets ALL requirements:")
    for key, value in reqs.items():
        status = "✓" if value else "✗"
        print(f"  {status} {key.replace('_', ' ')}: {value}")


if __name__ == "__main__":
    print("\n🚀 Day28 Change Manifest Validation Demo")
    print("Demonstrates CI/CD & AI Change Management")

    demo_valid_manifests()
    demo_invalid_manifests()
    demo_template()
    demo_requirements_check()

    print("\n" + "="*70)
    print("✓ Demo completed")
    print("="*70 + "\n")
