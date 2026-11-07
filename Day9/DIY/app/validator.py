"""把 Day9.md ⑩ 的概念驗收清單，變成可對 service_boundary.yaml 執行的結構檢查。

這不是在驗證程式碼行為（Day9.md 本身沒有程式），而是驗證「Service boundary 規格
本身有沒有把該填的東西填齊」——owner、required、expected_failure_behavior、
observable_signal 缺一項，就代表 dependency map 還沒做完；SLI 候選沒有明確
PROVEN/UNKNOWN 狀態，就代表還沒做到「先分清楚看得到與量得到」。
"""

from dataclasses import dataclass


REQUIRED_DEPENDENCY_FIELDS = (
    "name",
    "owner",
    "required",
    "expected_failure_behavior",
    "observable_signal",
)

CONTROL_PLANE_KEYWORDS = ("monitoring", "deploy", "control plane", "authorization", "監控", "部署")


@dataclass(frozen=True)
class ValidationResult:
    label: str
    passed: bool
    detail: str = ""


def validate_service_contract(spec: dict) -> ValidationResult:
    contract = (spec.get("service_contract") or "").strip()
    return ValidationResult(
        "① Service contract 是一句可辨識的使用者結果",
        passed=bool(contract),
        detail=contract or "缺少 service_contract",
    )


def validate_critical_path(spec: dict) -> ValidationResult:
    path = spec.get("critical_path") or []
    return ValidationResult(
        "② critical path 從 client 畫到 response",
        passed=len(path) >= 2,
        detail=f"目前只有 {len(path)} 個節點" if len(path) < 2 else " → ".join(path),
    )


def validate_dependencies(spec: dict) -> list[ValidationResult]:
    dependencies = spec.get("dependencies") or []
    results: list[ValidationResult] = []

    if not dependencies:
        results.append(
            ValidationResult("③ 至少列出一個依賴", passed=False, detail="dependencies 是空的")
        )
        return results

    for dep in dependencies:
        name = dep.get("name", "<unnamed>")
        missing = [
            field
            for field in REQUIRED_DEPENDENCY_FIELDS
            if not str(dep.get(field, "")).strip() and dep.get(field) is not True and dep.get(field) is not False
        ]
        results.append(
            ValidationResult(
                f"③ 依賴「{name}」欄位齊全（owner/required/failure behavior/signal）",
                passed=not missing,
                detail=f"缺少欄位：{missing}" if missing else "齊全",
            )
        )

    control_plane_covered = any(
        any(keyword.lower() in str(dep).lower() for keyword in CONTROL_PLANE_KEYWORDS)
        for dep in dependencies
    )
    results.append(
        ValidationResult(
            "⑥ Control plane（monitoring/deployment/authorization）也在依賴清單裡",
            passed=control_plane_covered,
            detail="有涵蓋" if control_plane_covered else "沒有任何依賴提到 monitoring/deploy/authorization",
        )
    )

    return results


def validate_candidate_slis(spec: dict) -> list[ValidationResult]:
    candidates = spec.get("candidate_slis") or []
    results: list[ValidationResult] = []

    if not candidates:
        results.append(
            ValidationResult("⑦ 至少評估一個候選 SLI", passed=False, detail="candidate_slis 是空的")
        )
        return results

    for candidate in candidates:
        name = candidate.get("name", "<unnamed>")
        status = candidate.get("status")
        reason = str(candidate.get("reason", "")).strip()
        valid_status = status in ("PROVEN", "UNKNOWN")
        has_reason = bool(reason)
        results.append(
            ValidationResult(
                f"⑦ 候選訊號「{name}」有明確 PROVEN/UNKNOWN 狀態與理由",
                passed=valid_status and has_reason,
                detail=f"status={status!r}, reason={'有' if has_reason else '缺'}",
            )
        )

    has_unknown = any(candidate.get("status") == "UNKNOWN" for candidate in candidates)
    results.append(
        ValidationResult(
            "⑦ 至少有一個訊號被誠實標成 UNKNOWN（不是每個 proxy 都直接升級成 SLI）",
            passed=has_unknown,
            detail="有" if has_unknown else "全部都是 PROVEN，值得重新檢查是不是太樂觀",
        )
    )

    return results


def validate(spec: dict) -> list[ValidationResult]:
    results = [
        validate_service_contract(spec),
        validate_critical_path(spec),
    ]
    results.extend(validate_dependencies(spec))
    results.extend(validate_candidate_slis(spec))
    return results
