"""
Main module demonstrating postmortem and runbook generation.

This script shows how to:
1. Create incident records programmatically
2. Generate postmortem markdown documents
3. Create and use runbooks
4. Understand the structure for incident response
"""

from datetime import datetime
from pathlib import Path
from app.models import Incident
from app.templates import (
    generate_postmortem_markdown,
    generate_postmortem_template,
    generate_runbook_template,
    generate_runbook_markdown
)


def save_postmortem(incident: Incident, output_dir: Path = Path("incidents")) -> Path:
    """Save a postmortem markdown document to disk."""
    output_dir.mkdir(exist_ok=True)

    filename = f"{incident.incident_id}_postmortem.md"
    filepath = output_dir / filename

    markdown = generate_postmortem_markdown(incident)
    filepath.write_text(markdown)

    print(f"✓ Postmortem saved: {filepath}")
    return filepath


def print_template_examples():
    """Print template examples for manual use."""

    print("\n" + "="*70)
    print("POSTMORTEM TEMPLATE (for manual use)")
    print("="*70)
    print(generate_postmortem_template())

    print("\n" + "="*70)
    print("RUNBOOK TEMPLATE (for manual use)")
    print("="*70)
    print(generate_runbook_template())


def generate_example_documents():
    """Generate example incident and runbook documents."""

    # Import examples
    from examples.example_incident_timeout import create_example_timeout_incident
    from examples.example_incident_ai_retrieval import create_example_ai_retrieval_incident
    from examples.example_runbook import create_example_runbook_entries

    output_dir = Path("incidents")
    output_dir.mkdir(exist_ok=True)

    print("="*70)
    print("GENERATING EXAMPLE INCIDENT DOCUMENTS")
    print("="*70)

    # Generate timeout incident
    print("\n1. Generating timeout incident postmortem...")
    timeout_incident = create_example_timeout_incident()
    save_postmortem(timeout_incident, output_dir)

    # Generate AI retrieval incident
    print("\n2. Generating AI retrieval incident postmortem...")
    ai_incident = create_example_ai_retrieval_incident()
    save_postmortem(ai_incident, output_dir)

    # Generate runbook
    print("\n3. Generating runbook from example entries...")
    runbook_entries = create_example_runbook_entries()
    runbook_markdown = generate_runbook_markdown(runbook_entries)

    runbook_path = output_dir / "RUNBOOK.md"
    runbook_path.write_text(runbook_markdown)
    print(f"✓ Runbook saved: {runbook_path}")

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\nGenerated files in {output_dir}/:")
    print(f"  - {timeout_incident.incident_id}_postmortem.md (Database timeout cascade)")
    print(f"  - {ai_incident.incident_id}_postmortem.md (AI retrieval stale index)")
    print(f"  - RUNBOOK.md (Common SRE issues and procedures)")
    print(f"\nNext steps:")
    print(f"  1. Review the generated postmortem documents")
    print(f"  2. Compare with the Day27 article structure")
    print(f"  3. Run: `python -m app.main --templates` to see blank templates")
    print(f"  4. Use the Pydantic models (app/models.py) to create your own incidents")


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--templates":
        print_template_examples()
    elif len(sys.argv) > 1 and sys.argv[1] == "--drill":
        from app.incident_drill import run_full_drill
        run_full_drill()
    else:
        generate_example_documents()


if __name__ == "__main__":
    main()
