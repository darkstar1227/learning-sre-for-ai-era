#!/usr/bin/env python3
"""
Test script for FastAPI endpoints using test client.

This script tests the endpoints without needing to start a server process.
"""

import sys
import json
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app.main import app


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def main():
    """Run all endpoint tests."""
    print("\n" + "=" * 70)
    print(" Day31 DIY: FastAPI Endpoint Tests")
    print("=" * 70)

    client = TestClient(app)
    tests_passed = 0
    tests_failed = 0

    # Test 1: Health check
    print_section("Test 1: Health Check (/health)")
    try:
        response = client.get("/health")
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")

        if response.status_code == 200 and result.get("status") == "ok":
            print("✓ PASSED")
            tests_passed += 1
        else:
            print("✗ FAILED")
            tests_failed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        tests_failed += 1

    # Test 2: Readiness check
    print_section("Test 2: Readiness Check (/ready)")
    try:
        response = client.get("/ready")
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")

        if response.status_code == 200 and result.get("status") == "ready":
            print("✓ PASSED")
            tests_passed += 1
        else:
            print("✗ FAILED")
            tests_failed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        tests_failed += 1

    # Test 3: Ask endpoint
    print_section("Test 3: Ask Endpoint (/ask)")
    try:
        payload = {
            "question": "遠端工作是否需要主管核准？",
            "actor_role": "employee",
        }

        response = client.post("/ask", json=payload)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\nResponse:")
            print(f"  request_id: {result['request_id']}")
            print(f"  task_id: {result['task_id']}")
            print(f"  question: {result['question']}")
            print(f"  answer length: {len(result['answer'])} chars")
            print(f"  citations: {result['citations']}")
            print(f"  quality_status: {result['quality_status']}")
            print(f"  task_status: {result['task_status']}")

            # Verify structure
            required_fields = ["request_id", "task_id", "question", "answer", "citations", "quality_status", "task_status"]
            if all(field in result for field in required_fields):
                print("\n✓ PASSED (all required fields present)")
                tests_passed += 1
            else:
                print("\n✗ FAILED (missing required fields)")
                tests_failed += 1
        else:
            print(f"Error: {response.text}")
            print("✗ FAILED")
            tests_failed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        tests_failed += 1

    # Test 4: Get regression dataset
    print_section("Test 4: Get Regression Dataset (/dataset/regression)")
    try:
        response = client.get("/dataset/regression")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            dataset = response.json()
            print(f"\nDataset Info:")
            print(f"  dataset_id: {dataset['dataset_id']}")
            print(f"  version: {dataset['version']}")
            print(f"  examples: {len(dataset['examples'])}")

            print(f"\nExamples:")
            for ex in dataset["examples"]:
                print(f"  • {ex['example_id']}")

            if len(dataset["examples"]) == 3:
                print("\n✓ PASSED (correct number of examples)")
                tests_passed += 1
            else:
                print(f"\n✗ FAILED (expected 3 examples, got {len(dataset['examples'])})")
                tests_failed += 1
        else:
            print(f"Error: {response.text}")
            print("✗ FAILED")
            tests_failed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        tests_failed += 1

    # Test 5: Evaluate
    print_section("Test 5: Evaluate (/evaluate)")
    try:
        baseline_output = {
            "question": "遠端工作是否需要主管核准？",
            "answer": "Based on company policy, remote work requires manager approval.",
            "citations": ["company-policy-remote-work"],
            "quality_status": "approved",
        }

        candidate_output = {
            "question": "遠端工作是否需要主管核准？",
            "answer": "Yes, manager approval is needed.",
            "citations": ["company-policy-remote-work"],
            "quality_status": "approved",
        }

        payload = {
            "baseline_outputs": baseline_output,
            "candidate_outputs": candidate_output,
        }

        response = client.post("/evaluate", json=payload)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\nEvaluation Result:")
            print(f"  decision: {result['decision']}")
            print(f"  rationale: {result['rationale']}")
            print(f"  required_source_failures: {result['required_source_failures']}")
            print(f"  safety_failures: {result['safety_failures']}")
            print(f"  quality_regressions: {result['quality_regressions']}")

            # Verify decision is valid
            if result['decision'] in ["blocked", "human_review_required", "allowed"]:
                print("\n✓ PASSED (valid decision)")
                tests_passed += 1
            else:
                print("\n✗ FAILED (invalid decision)")
                tests_failed += 1
        else:
            print(f"Error: {response.text}")
            print("✗ FAILED")
            tests_failed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        tests_failed += 1

    # Test 6: Trace example
    print_section("Test 6: Trace Example (/trace-example)")
    try:
        response = client.get("/trace-example")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\nTrace Example Result:")
            print(f"  request_id: {result['request_id']}")
            print(f"  task_id: {result['task_id']}")
            print(f"  langsmith_enabled: {result['langsmith_enabled']}")
            print(f"  langsmith_project: {result['langsmith_project']}")
            print(f"  answer_length: {result['result_summary']['answer_length']}")
            print(f"  citations_count: {result['result_summary']['citations_count']}")

            if all(k in result for k in ["request_id", "task_id", "langsmith_enabled", "langsmith_project"]):
                print("\n✓ PASSED (all fields present)")
                tests_passed += 1
            else:
                print("\n✗ FAILED (missing fields)")
                tests_failed += 1
        else:
            print(f"Error: {response.text}")
            print("✗ FAILED")
            tests_failed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        tests_failed += 1

    # Summary
    print_section("Test Summary")
    total = tests_passed + tests_failed
    print(f"Passed: {tests_passed}/{total}")
    print(f"Failed: {tests_failed}/{total}")

    if tests_failed == 0:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {tests_failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
