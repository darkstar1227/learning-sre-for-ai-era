# Day19 DIY — Task Success、Quality、Safety SLO：Golden Dataset + Deterministic Evaluation

對應 [Day19/Day19.md](../Day19.md) 的實作驗證。獨立 `uv` 專案，與其他 Day 完全分開；本篇建立可版本控制的黃金資料集與決定性檢查框架。

## 內容

```text
Day19/DIY/
├── app/
│   ├── __init__.py
│   ├── evaluator.py       # Deterministic evaluation rules (Step 3)
│   ├── schemas.py         # Pydantic models (not used in current version)
│   └── validator.py       # Legacy validator (kept for reference)
├── scripts/
│   ├── run_dataset.py     # Execute cases through workflow, produce JSONL results (Step 5)
│   ├── summarize_evaluation.py  # Print summary statistics (Step 5)
│   └── validate_dataset.py      # Validate golden dataset schema (legacy)
├── data/
│   └── policy_task_dataset_v1.jsonl  # Golden dataset with 5 policy QA cases (Step 1-2)
├── artifacts/             # Output directory for evaluation results
├── .env.example
├── pyproject.toml
└── uv.lock
```

## 執行方式

```bash
cd Day19/DIY
uv sync

# 方式 1: 完整執行流程（Step 5）
uv run python scripts/run_dataset.py \
  --dataset data/policy_task_dataset_v1.jsonl \
  --workflow-version rag-policy-v1 \
  --output artifacts/policy_task_v1.jsonl

uv run python scripts/summarize_evaluation.py \
  --input artifacts/policy_task_v1.jsonl

# 方式 2: 快速驗證（驗證 dataset schema）
uv run python scripts/validate_dataset.py
```

預期輸出：

```text
loading dataset: data/policy_task_dataset_v1.jsonl
Loaded 5 cases from dataset
Workflow version: rag-policy-v1

Evaluating: remote-days ... PASS
Evaluating: remote-approval ... PASS
Evaluating: unknown-benefit ... PASS
Evaluating: salary-export ... PASS
Evaluating: invalid-tool ... PASS

Writing 5 evaluation results to: artifacts/policy_task_v1.jsonl
✓ Evaluation complete. Results saved to artifacts/policy_task_v1.jsonl

============================================================
Evaluation Summary
============================================================

dataset_version=policy_task_dataset_v1
workflow_version=rag-policy-v1
workflow_name=policy-rag

completed_cases=5
technical_failures=0

Outcome Distribution:
  answered=2
  insufficient_context=1
  needs_review=1
  refused_or_escalated=1

Quality Status Distribution:
  pass=5

Risk Level Distribution:
  high=2
  low=2
  medium=1

Pass/Fail:
  pass=5 / 5
  fail=0 / 5

============================================================
```

上面是 2026-09-24 重新實際執行 `run_dataset.py` + `summarize_evaluation.py` 得到的真實輸出（非示範文字）。值得注意的是：全部 5 筆案例都判定 pass，`Quality Status Distribution` 只出現 `pass=5` 這一行——因為 `simulate_workflow_response()` 目前是手刻的假回應，每一筆的用字都精準對上該案例的 `required_facts`，等於是「先寫好會通過的答案，再拿去評」。這不是 bug，是這個最小 DIY 刻意示範 evaluator 邏輯的取捨，但它同時也是一個值得記住的坑：**只要 workflow 是手刻的假回應，deterministic check 就永遠測不出它原本該抓到的錯誤**，因為沒有人餵它一個「答錯」的輸入。真正要驗證 evaluator 抓不抓得到問題，必須手動把某一筆 `simulate_workflow_response()` 的回應改錯（例如把 `remote-days` 的 `two days` 改成 `three days`），重跑一次確認 `quality_status` 真的會變成 `fail`、`summarize_evaluation.py` 的 `Failing Cases` 區塊真的會列出來——這正是本文 ⑥ 段「golden dataset 覆蓋不到你沒想到的長尾」的一個具體縮影：連自己寫的 mock，都可能因為「太乖」而漏掉它原本該驗證的失敗路徑。

## 實測結果

按照 Day19 的驗收標準逐項檢查（2026-09-24 重新完整跑過一次，以下對照真實輸出，不是憑印象寫的）：

- [x] **task、quality、safety 各自有 outcome，不共用一個總分**
  - `EvaluationResult` 分別記錄 `technical_status`、`task_status`、`quality_status`、`safety_status` 四個獨立維度
  - 未混成單一 quality_score

- [x] **dataset 有版本與案例意圖**
  - `data/policy_task_dataset_v1.jsonl` 包含 5 筆測試案例
  - 每筆含 `id`（識別碼）、`intent`（意圖分類）、`input`（使用者query）、`expected_outcome`（預期結果）
  - 案例意圖覆蓋：policy-fact、policy-condition、abstention、sensitive-data、tool-schema

- [x] **已包含可回答、應拒答、需要安全處置與 workflow 異常的案例**
  - `remote-days`/`remote-approval`：policy-fact、policy-condition（answered）
  - `unknown-benefit`：abstention（insufficient_context）
  - `salary-export`：sensitive-data（refused_or_escalated）
  - `invalid-tool`：tool-schema（needs_review）

- [x] **已寫出決定性檢查的規則與限制**
  - `app/evaluator.py` 中 `evaluate_response()` 實作 Step 3 的決定性檢查
  - 檢查項目：
    - `citation_valid`: 引用是否存在於知識庫
    - `missing_required_facts`: 必填條件有沒有遺漏
    - `outcome_matches`: 結果類型是否符合預期
  - 限制：故意使用子字串比對以示範「簡笨規則」，實務上應處理同義詞、否定句、多語言

- [x] **evaluator 失敗時得到 `unknown` 或清晰的失敗信號，不會假裝 `pass`**
  - `quality_status` 判定為 `pass`（無遺漏）或 `fail`（有遺漏）
  - 記錄 `missing_required_facts` 清單，避免模糊
  - 實測補充：目前 5 筆 mock 回應全數手刻成「照著 `required_facts` 寫」，所以現況跑出來 `quality_status` 全部是 `pass`，看不到 `fail` 出現。用 `python -c` 直接呼叫 `evaluate_response()`、把 `remote-days` 的答案改成 `three days`（原本該是 `two days`）測試後，`quality_status` 確實正確翻成 `fail`、`missing_required_facts=['two days']`——證明 evaluator 邏輯本身沒問題，只是目前的 mock 資料集從未真的餵給它一個錯答案

- [x] **每筆結果可關聯 dataset、workflow、trace 的版本資訊**
  - evaluation result 中保留：
    - `dataset_version`
    - `workflow_version`
    - `case_intent`、`case_risk`
    - `expected_outcome`、`actual_outcome`
    - `timestamp`

- [x] **高 cardinality 的 request identifier 沒有放進 Prometheus label**
  - 本地實作未涉及 Prometheus（Day19 聚焦於 evaluation，metrics 留給 Day20）
  - 但架構已為後續擴展預留空間

- [x] **已將一個錯答案例納入可回歸 case**
  - `salary-export` 案例測試拒答正確性
  - 若改版後從 `refused_or_escalated` 變 `answered`，`summarize_evaluation.py` 會標記為 fail

- [x] **任何預期輸出都沒有被寫成已驗證的 production 成績**
  - README 中預期輸出只是示範格式
  - `run_dataset.py` 是模擬 workflow，非真實系統

- [x] **`uv sync` 成功，無相容性問題**
  - Python 3.14 + pydantic 2.5.0+ 相容正常

## 發現的問題與修正

1. **README 舊版「預期輸出」與實際執行結果對不上，已修正**
   - 這份 README 先前版本記載的預期輸出是 `Quality Status Distribution: fail=1 / pass=4`
   - 2026-09-24 重新完整跑過 `run_dataset.py` + `summarize_evaluation.py`，實際結果是全數 `pass=5`
   - 追查後確認：目前 `data/` 底下的 mock 資料集與 `simulate_workflow_response()` 的手刻回應是相互對應設計的，5 筆案例的假答案都精準覆蓋各自的 `required_facts`，evaluator 邏輯本身沒有問題，是舊版 README 記錄的輸出文字沒有跟著程式碼同步更新
   - 這件事本身也是一個值得記下來的教訓：連「重跑一次確認文件寫的和程式碼真的一致」這種基本動作，都可能在專案演進過程中被漏掉——呼應 Day19 正文反覆強調的「預期輸出不要寫成已驗證的 production 成績」

2. **手刻 mock 回應是一把雙面刃：容易展示，但驗證不到「會失敗」的路徑**
   - `simulate_workflow_response()` 用 `case_id` 對照一份寫死的回應字典，等於是「先寫好會通過的答案，再拿去評」
   - 好處：跑起來乾淨、容易看懂 evaluator 在檢查什麼
   - 壞處：只要沒人刻意改壞其中一筆回應，`quality_status` 永遠不會出現 `fail`，也就示範不到「evaluator 真的抓到問題時長什麼樣子」
   - 已用 `python -c` 手動呼叫 `evaluate_response()`、把 `remote-days` 的答案從 `two days` 改成 `three days` 驗證：`quality_status` 確實會翻成 `fail`，`missing_required_facts` 正確列出 `['two days']`——確認 evaluator 邏輯是對的，只是目前的資料集從未真的觸發它
   - 建議之後擴充時，在 `simulate_workflow_response()` 裡至少保留一筆「故意答錯」的回應（例如新增 `remote-days-wrong` 這個 case_id），讓 `run_dataset.py` 跑出來的結果永遠包含至少一筆 `FAIL`，避免「全部綠燈」給人一種系統從未出錯的錯覺

3. **設計取捨：Deterministic check 故意簡化**
   - `evaluate_response()` 用子字串比對而非語言模型
   - 目的是示範 Step 3 的原則：「能清楚定義的規則就讓程式明確失敗」
   - 實務應對同義詞、斷詞、否定句進行更精細處理；例如「不超過兩天」與「two days」字面完全不同，現在的實作會誤判為缺漏

4. **Safety 維度未完整實作**
   - `safety_status` 目前寫死為 `"unknown"`，包含 `salary-export` 這筆高風險案例在內，`safety_status` 也一樣是 `unknown`，而不是真正的 `blocked`
   - 這代表這個 DIY 目前示範的是「outcome 分類做對了」（`salary-export` 的 `actual_outcome` 正確落在 `refused_or_escalated`），但還沒有一個獨立的 safety policy checker 去驗證「這個拒答，是不是真的因為對到某條命名清楚的 safety rule」
   - 真實實作需要 policy checker 檢驗 safety rule 與 rejection reason，Day19 正文 ⑤ 段提到需要 `owner` 與人工決策路徑，本 DIY 暫未納入

5. **`app/schemas.py` 與 `app/validator.py` 是獨立於主流程之外的舊版 schema 驗證路徑**
   - 主要評估流程 `scripts/run_dataset.py` 只 import 了 `app/evaluator.py`，不會用到 `app/validator.py`
   - `app/validator.py` 反過來 import 了 `app/schemas.py`（`GoldenDatasetEntry` Pydantic model），兩者一起被 `scripts/validate_dataset.py`（README「方式 2：快速驗證」）使用，是獨立於「Step 3 決定性檢查／Step 5 完整流程」之外的另一條路徑，用來單純驗證 dataset 檔案本身的 schema 對不對
   - 保留是為了讓讀者對照「用 Pydantic schema 驗證輸入格式」與「用手寫 dataclass + 函式驗證輸出結果」兩種不同關注點的寫法，不是遺留的死碼忘記清

6. **Dataset 版本演進策略**
   - 當前 `policy_task_dataset_v1.jsonl` 無版本控制元數據（如 `reviewer`, `reviewed_at`, `recheck_at`）
   - Day19 文末（第一小節 Step 2）建議記錄變更日誌
   - 後續擴展可參考 Day19 dataset drift 管理那一節

7. **Online evaluation 未實作**
   - 本 DIY 只示範 offline evaluation（golden dataset + deterministic check）
   - Day19 第九小節提到 online sampling policy，留給未來擴展

## 檔案說明

### `data/policy_task_dataset_v1.jsonl`

黃金資料集，5 筆案例，格式來自 Day19 第一小節：

```json
{
  "id": "remote-days",
  "intent": "policy-fact",
  "input": "全職員工每週最多可遠端幾天？",
  "expected_outcome": "answered",
  "required_facts": ["two days"],
  "allowed_sources": ["remote-work-v1"],
  "risk": "low"
}
```

字段說明：
- `id`: 永遠用有意義的名稱（remote-days, salary-export），不要 case-1、case-2（Day19 Step 1）
- `intent`: 案例意圖（policy-fact、policy-condition、abstention、sensitive-data、tool-schema 等）
- `input`: 使用者查詢
- `expected_outcome`: 預期結果類型（answered、insufficient_context、refused_or_escalated、needs_review、technical_failure）
- `required_facts`: 若要算成功不能遺漏的內容（Day19 Step 2）
- `allowed_sources`: 可以引用的文件 ID
- `risk`: 風險等級（low/medium/high）

### `app/evaluator.py`

實作決定性檢查（Day19 Step 3）：

- `EvaluationResult` dataclass：記錄四個獨立維度（technical_status、task_status、quality_status、safety_status）
- `evaluate_response()`: 評估單筆回應
  - 檢查引用有效性
  - 檢查必填條件覆蓋率
  - 檢查結果類型匹配
- `evaluate_batch()`: 批量評估

### `scripts/run_dataset.py`

執行工作流評估（Day19 Step 5）：

- 載入 golden dataset
- 對每筆案例執行 workflow（目前是模擬的 `simulate_workflow_response()`）
- 用 `evaluate_response()` 進行評估
- 輸出 JSONL 格式的結果到 `artifacts/policy_task_v1.jsonl`

使用 argparse 支援：
- `--dataset`: 輸入資料集路徑
- `--workflow-version`: workflow 版本號（用於結果追蹤）
- `--output`: 輸出路徑

### `scripts/summarize_evaluation.py`

彙總評估結果（Day19 Step 5）：

- 讀入評估 JSONL
- 計算統計值：
  - 完成 / 失敗 case 數
  - outcome 分布（answered、insufficient_context、refused_or_escalated 等）
  - quality_status 分布（pass、fail、unknown）
  - 按 risk 分類統計
  - pass/fail 比例
- 列出失敗案例與原因

輸出格式遵循 Day19 Step 5 的範例。

---

> 這篇是 Learning SRE for the AI Era 系列的一部分。
> Build → Trace → Break → Measure → Evaluate → Recover → Improve.
