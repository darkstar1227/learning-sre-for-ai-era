#!/usr/bin/env python3
"""
Test script for FastAPI endpoints.

This script tests the LangSmith-integrated FastAPI server endpoints:
- /ask - main workflow endpoint
- /dataset/regression - get regression dataset
- /evaluate - evaluate candidate vs baseline
- /trace-example - run sample workflow
"""

import sys
import json
import subprocess
import time
import requests


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def start_server():
    """Start the FastAPI server."""
    print_section("Starting FastAPI Server")

    # Start server in background
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(2)

    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("✓ Server started successfully")
            return process
    except requests.RequestException:
        pass

    print("✗ Server failed to start")
    return None


def test_health():
    """Test /health endpoint."""
    print_section("Test 1: Health Check")

    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_ready():
    """Test /ready endpoint."""
    print_section("Test 2: Readiness Check")

    try:
        response = requests.get("http://localhost:8000/ready")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_ask():
    """Test /ask endpoint."""
    print_section("Test 3: Ask Endpoint")

    try:
        payload = {
            "question": "遠端工作是否需要主管核准？",
            "actor_role": "employee",
        }

        response = requests.post("http://localhost:8000/ask", json=payload)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\nResponse:")
            print(f"  request_id: {result['request_id']}")
            print(f"  task_id: {result['task_id']}")
            print(f"  question: {result['question']}")
            print(f"  answer: {result['answer']}")
            print(f"  citations: {result['citations']}")
            print(f"  quality_status: {result['quality_status']}")
            print(f"  task_status: {result['task_status']}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_dataset():
    """Test /dataset/regression endpoint."""
    print_section("Test 4: Get Regression Dataset")

    try:
        response = requests.get("http://localhost:8000/dataset/regression")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            dataset = response.json()
            print(f"\nDataset Info:")
            print(f"  dataset_id: {dataset['dataset_id']}")
            print(f"  version: {dataset['version']}")
            print(f"  examples: {len(dataset['examples'])}")

            print(f"\nExamples:")
            for ex in dataset["examples"]:
                print(f"  • {ex['example_id']}: {ex['inputs']['question']}")

            return len(dataset["examples"]) > 0
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_evaluate():
    """Test /evaluate endpoint."""
    print_section("Test 5: Evaluate Candidate vs Baseline")

    try:
        baseline_output = {
            "question": "遠端工作是否需要主管核准？",
            "answer": "Based on company policy, remote work requires manager approval.",
            "citations": ["company-policy-remote-work"],
            "quality_status": "approved",
        }

        candidate_output = {
            "question": "遠端工作是否需要主管核准？",
            "answer": "Yes, you need manager approval.",
            "citations": ["company-policy-remote-work"],
            "quality_status": "approved",
        }

        payload = {
            "baseline_outputs": baseline_output,
            "candidate_outputs": candidate_output,
        }

        response = requests.post("http://localhost:8000/evaluate", json=payload)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\nEvaluation Result:")
            print(f"  decision: {result['decision']}")
            print(f"  rationale: {result['rationale']}")
            print(f"  required_source_failures: {result['required_source_failures']}")
            print(f"  safety_failures: {result['safety_failures']}")
            print(f"  quality_regressions: {result['quality_regressions']}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_trace_example():
    """Test /trace-example endpoint."""
    print_section("Test 6: Trace Example")

    try:
        response = requests.get("http://localhost:8000/trace-example")
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
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" Day31 DIY: FastAPI Endpoint Tests")
    print("=" * 70)

    # Start server
    server = start_server()
    if not server:
        print("Failed to start server")
        return 1

    try:
        # Run tests
        tests = [
            ("Health Check", test_health),
            ("Readiness Check", test_ready),
            ("Ask Endpoint", test_ask),
            ("Regression Dataset", test_dataset),
            ("Evaluate", test_evaluate),
            ("Trace Example", test_trace_example),
        ]

        passed = 0
        failed = 0

        for name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                    print(f"✓ {name} PASSED")
                else:
                    failed += 1
                    print(f"✗ {name} FAILED")
            except Exception as e:
                failed += 1
                print(f"✗ {name} FAILED: {e}")

        # Summary
        print_section("Test Summary")
        print(f"Passed: {passed}/{len(tests)}")
        print(f"Failed: {failed}/{len(tests)}")

        if failed == 0:
            print("\n✓ All tests passed!")
            return 0
        else:
            print(f"\n✗ {failed} test(s) failed")
            return 1

    finally:
        # Stop server
        print("\nStopping server...")
        server.terminate()
        server.wait()


if __name__ == "__main__":
    sys.exit(main())
