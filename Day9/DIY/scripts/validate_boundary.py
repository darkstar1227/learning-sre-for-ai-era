"""跑 service_boundary.yaml，對照 Day9.md ⑩ 的概念驗收清單做結構檢查。"""

from pathlib import Path

import yaml

from app.validator import validate


SPEC_PATH = Path("service_boundary.yaml")


def main() -> None:
    spec = yaml.safe_load(SPEC_PATH.read_text())

    results = validate(spec)

    failures = [r for r in results if not r.passed]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.label} — {result.detail}")

    print()
    if failures:
        print(f"{len(failures)} 項沒通過。")
        raise SystemExit(1)

    print("service_boundary.yaml 通過 Day9.md ⑩ 的結構檢查。")


if __name__ == "__main__":
    main()
