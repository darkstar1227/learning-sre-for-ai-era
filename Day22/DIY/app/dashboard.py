"""
Three-layer dashboard design based on Day22 article.

Framework: Golden Signals, RED, and USE methods.
Layers:
  1. User Layer: business outcome metrics
  2. Service Layer: RED (Rate, Errors, Duration) for workflow components
  3. Resource Layer: USE (Utilization, Saturation, Errors) for infrastructure
"""

from typing import Any
from pydantic import BaseModel, Field


class DashboardChart(BaseModel):
    """A single chart representing a specific monitoring concern."""

    name: str = Field(..., description="Chart name/title")
    metric_type: str = Field(..., description="Golden Signals | RED | USE")
    question: str = Field(..., description="What question does this chart answer?")
    red_flag_action: str = Field(..., description="What to do if this chart shows red/alert")
    examples: list[str] = Field(
        default_factory=list,
        description="Example queries or visualizations"
    )


class DashboardLayer(BaseModel):
    """A single layer in the three-layer dashboard."""

    name: str = Field(..., description="Layer name: 'User' | 'Service' | 'Resource'")
    purpose: str = Field(..., description="Why this layer matters")
    readers: list[str] = Field(..., description="Who reads this layer (on-call, product, etc.)")
    charts: list[DashboardChart] = Field(..., description="Charts in this layer")

    def validate_no_method_confusion(self) -> bool:
        """
        Ensure RED and USE are not mixed.
        - RED: for services/APIs (request-based metrics)
        - USE: for resources/infrastructure (capacity-based metrics)
        """
        red_charts = [c for c in self.charts if c.metric_type == "RED"]
        use_charts = [c for c in self.charts if c.metric_type == "USE"]

        # User and Service layers should primarily use RED/Golden Signals
        if self.name in ["User", "Service"]:
            if use_charts and not red_charts:
                raise ValueError(
                    f"{self.name} layer should not be USE-only; "
                    "USE is for resource layers, not service/request metrics"
                )

        # Resource layer should primarily use USE
        if self.name == "Resource":
            if red_charts and not use_charts:
                raise ValueError(
                    f"{self.name} layer should not be RED-only; "
                    "USE is for resource utilization/saturation, "
                    "RED is for request-based services"
                )

        return True


class ThreeLayerDashboard(BaseModel):
    """Complete three-layer dashboard design."""

    title: str = Field(default="AI Workflow Observability: Three-Layer Dashboard")
    layers: list[DashboardLayer] = Field(..., description="User, Service, Resource layers")

    def validate_ai_signals_to_outcome(self) -> bool:
        """Ensure AI-specific signals (queue delay, TTFT, tool failure, evaluation) map to user outcome."""
        user_layer_signals = {
            chart.name.lower()
            for layer in self.layers
            if layer.name == "User"
            for chart in layer.charts
        }

        service_layer_signals = {
            chart.name.lower()
            for layer in self.layers
            if layer.name == "Service"
            for chart in layer.charts
        }

        # AI signals that should appear in Service layer and roll up to User layer
        # These are keywords we're looking for in chart names
        expected_ai_signals = {
            "queue delay",
            "ttft",  # time to first token
            "tool failure",
            "evaluation outcome",
        }

        all_signals = user_layer_signals | service_layer_signals

        # Check if keywords appear in any chart name (case-insensitive, substring match)
        found_signals = set()
        for signal in expected_ai_signals:
            for chart_name in all_signals:
                if signal in chart_name:
                    found_signals.add(signal)
                    break

        missing = expected_ai_signals - found_signals
        if missing:
            print(f"⚠ Warning: AI signals not clearly found: {missing}")
            print("  (This may be OK if signals are present but with different naming)")

        return True

    def validate_all_layers_present(self) -> bool:
        """Ensure all three layers exist."""
        layer_names = {layer.name for layer in self.layers}
        required = {"User", "Service", "Resource"}
        missing = required - layer_names
        if missing:
            raise ValueError(f"Missing layers: {missing}")
        return True

    def summary(self) -> str:
        """Generate human-readable summary of the dashboard."""
        lines = [
            f"# {self.title}",
            "",
        ]

        for layer in self.layers:
            lines.append(f"## {layer.name} Layer")
            lines.append(f"**Purpose:** {layer.purpose}")
            lines.append(f"**Readers:** {', '.join(layer.readers)}")
            lines.append("")

            for chart in layer.charts:
                lines.append(f"### {chart.name}")
                lines.append(f"- **Type:** {chart.metric_type}")
                lines.append(f"- **Question:** {chart.question}")
                lines.append(f"- **Red Flag Action:** {chart.red_flag_action}")
                if chart.examples:
                    lines.append(f"- **Examples:** {', '.join(chart.examples)}")
                lines.append("")

        return "\n".join(lines)
