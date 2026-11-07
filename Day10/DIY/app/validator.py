"""
Validator for Day10 Fault-Error-Failure analysis document.

Checks if a failure_analysis.md file meets the requirements from Day10.md section ④:
- Clear user-observable failure statement
- Multiple error hypotheses (not just one)
- Testable error conditions with observable signals
- Specific, actionable fault examples
- Actions specified for each layer (Failure/Error/Fault)
- No unproven faults claimed as root cause
- Semantic failure acknowledged
- Control plane failures acknowledged
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple


class FailureAnalysisValidator:
    """Validates a failure analysis document against Day10 requirements."""

    def __init__(self, markdown_path: Path):
        self.markdown_path = Path(markdown_path)
        self.content = ""
        self.checks_passed: List[str] = []
        self.checks_failed: List[Tuple[str, str]] = []

    def load_document(self) -> bool:
        """Load and parse the markdown document."""
        if not self.markdown_path.exists():
            self.checks_failed.append(("Document Existence", f"File not found: {self.markdown_path}"))
            return False

        try:
            self.content = self.markdown_path.read_text(encoding="utf-8")
            return True
        except Exception as e:
            self.checks_failed.append(("Document Reading", str(e)))
            return False

    def check_failure_definition(self) -> bool:
        """Verify: Clear failure statement that answers 'what does user not get?'"""
        # Look for explicit "User Observable" or similar section with clear failure statement
        # Look for patterns that describe what user cannot get
        failure_patterns = [
            r"User Observable",
            r"employee.*cannot",
            r"cannot.*retrieve",
            r"cannot.*get",
            r"no.*response",
            r"cannot.*answer",
            r"fails to.*get",
        ]

        has_failure_section = re.search(r"##\s+.*Failure|User Observable", self.content, re.IGNORECASE)
        has_failure_statement = any(
            re.search(pattern, self.content, re.IGNORECASE) for pattern in failure_patterns
        )

        if has_failure_section and has_failure_statement:
            self.checks_passed.append("✓ Failure clearly defined (user cannot get response)")
            return True

        self.checks_failed.append(("Failure Definition", "No clear user-observable failure statement"))
        return False

    def check_multiple_error_hypotheses(self) -> bool:
        """Verify: Multiple error hypotheses, not just one."""
        # Look for error table or multiple error sections
        error_patterns = [
            r"Error.*Hypothesis",
            r"\|\s*Error\s+Hypothesis",
            r"error\s+condition",
            r"could\s+trigger",
        ]

        error_count = len(re.findall(r"Error Hypothesis|error.*condition", self.content, re.IGNORECASE))

        if error_count >= 2:
            self.checks_passed.append(f"✓ Multiple error hypotheses ({error_count} listed)")
            return True

        self.checks_failed.append(
            ("Multiple Errors", f"Only {error_count} error hypothesis found, need at least 2")
        )
        return False

    def check_observable_signals(self) -> bool:
        """Verify: Each error hypothesis has observable signals (metrics/logs/traces)."""
        # Look for signal names in tables or descriptions
        signal_keywords = [
            "latency",
            "error_rate",
            "errors_total",
            "signal",
            "metric",
            "trace",
            "log",
            "status",
            "up",
            "down",
        ]

        signal_count = 0
        for keyword in signal_keywords:
            signal_count += len(re.findall(rf"\b{keyword}\b", self.content, re.IGNORECASE))

        if signal_count >= 8:  # Reasonable threshold for multiple error hypotheses
            self.checks_passed.append(f"✓ Observable signals referenced ({signal_count} signal terms)")
            return True

        self.checks_failed.append(("Observable Signals", f"Insufficient observable signals (found {signal_count})"))
        return False

    def check_fault_examples(self) -> bool:
        """Verify: Specific, actionable fault examples (not generic 'code is broken')."""
        # Look for Layer 3 or Fault section
        if "Layer 3" not in self.content and "FAULT" not in self.content:
            self.checks_failed.append(("Fault Definition", "No Layer 3 (Fault) section found"))
            return False

        # Check for concrete examples
        fault_keywords = [
            "timeout",
            "configuration",
            "connection pool",
            "code review",
            "test",
            "exception",
            "fallback",
        ]

        fault_mentions = 0
        for keyword in fault_keywords:
            fault_mentions += len(re.findall(rf"\b{keyword}\b", self.content, re.IGNORECASE))

        if fault_mentions >= 5:
            self.checks_passed.append(f"✓ Specific fault examples ({fault_mentions} fault-related terms)")
            return True

        self.checks_failed.append(("Fault Examples", f"Insufficient specific faults (found {fault_mentions})"))
        return False

    def check_actions_for_each_layer(self) -> bool:
        """Verify: Actions specified for Failure, Error, and Fault layers."""
        layers = {"Failure": False, "Error": False, "Fault": False}

        for layer in layers.keys():
            # Look for the layer section and following checkboxes or action items
            if re.search(rf"##.*{layer}|On {layer}", self.content, re.IGNORECASE):
                # Check if there are action items (bullets or checkboxes)
                if re.search(r"[-\*]\s+\[\s*\]|[-\*]\s+[A-Z]", self.content):
                    layers[layer] = True

        if all(layers.values()):
            self.checks_passed.append("✓ Actions specified for all three layers (Failure/Error/Fault)")
            return True

        missing = [k for k, v in layers.items() if not v]
        self.checks_failed.append(("Actions by Layer", f"Missing actions for: {', '.join(missing)}"))
        return False

    def check_no_unproven_root_cause(self) -> bool:
        """Verify: No unproven fault written as definitive root cause."""
        # Look for hedging language: hypothesis, possible, may, could, if
        # Look for statements that sound definitive: "is", "was", "problem was"

        definitive_patterns = [r"the\s+problem\s+was", r"root\s+cause\s+is\s+", r"^proof\s+that"]

        definitive_count = len(re.findall(r"the\s+problem\s+was|root\s+cause\s+is", self.content, re.IGNORECASE))

        hypothesis_count = len(re.findall(r"hypothesis|possible|may|could|if|assume", self.content, re.IGNORECASE))

        if definitive_count == 0 or hypothesis_count > definitive_count:
            self.checks_passed.append("✓ No unproven faults claimed as root cause (uses 'hypothesis' language)")
            return True

        self.checks_failed.append(("Root Cause Language", "Contains definitive fault claims without proof"))
        return False

    def check_semantic_failure(self) -> bool:
        """Verify: Semantic failure acknowledged (answer could be wrong even with HTTP 200)."""
        semantic_terms = [
            "semantic",
            "incomplete context",
            "wrong answer",
            "http 200",
            "evaluation",
            "quality",
            "ungrounded",
        ]

        semantic_mentions = 0
        for term in semantic_terms:
            semantic_mentions += len(re.findall(rf"\b{re.escape(term)}\b", self.content, re.IGNORECASE))

        if semantic_mentions >= 3:
            self.checks_passed.append("✓ Semantic failure acknowledged")
            return True

        self.checks_failed.append(("Semantic Failure", "Semantic failure not adequately addressed"))
        return False

    def check_control_plane(self) -> bool:
        """Verify: Control plane failures (monitoring/deployment) acknowledged."""
        control_terms = [
            "monitoring",
            "tracing",
            "deployment",
            "control plane",
            "observability",
            "pipeline",
        ]

        control_mentions = 0
        for term in control_terms:
            control_mentions += len(re.findall(rf"\b{re.escape(term)}\b", self.content, re.IGNORECASE))

        if control_mentions >= 2:
            self.checks_passed.append("✓ Control plane failures acknowledged")
            return True

        self.checks_failed.append(("Control Plane", "Control plane failures not addressed"))
        return False

    def run_all_checks(self) -> bool:
        """Run all validation checks."""
        if not self.load_document():
            return False

        checks = [
            self.check_failure_definition,
            self.check_multiple_error_hypotheses,
            self.check_observable_signals,
            self.check_fault_examples,
            self.check_actions_for_each_layer,
            self.check_no_unproven_root_cause,
            self.check_semantic_failure,
            self.check_control_plane,
        ]

        for check in checks:
            check()

        return len(self.checks_failed) == 0

    def report(self) -> str:
        """Generate validation report."""
        output = []
        output.append("=" * 70)
        output.append("Day10 Failure Analysis Validation Report")
        output.append("=" * 70)

        if self.checks_passed:
            output.append("\n✓ PASSED CHECKS:")
            for check in self.checks_passed:
                output.append(f"  {check}")

        if self.checks_failed:
            output.append("\n✗ FAILED CHECKS:")
            for check_name, reason in self.checks_failed:
                output.append(f"  [{check_name}] {reason}")

        passed = len(self.checks_passed)
        total = passed + len(self.checks_failed)
        output.append("\n" + "=" * 70)
        output.append(f"Result: {passed}/{total} checks passed")

        if len(self.checks_failed) == 0:
            output.append("Status: PASS")
        else:
            output.append("Status: FAIL")

        output.append("=" * 70)

        return "\n".join(output)
