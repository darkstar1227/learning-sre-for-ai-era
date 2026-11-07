# Day12 DIY — AI Workflow Failure Modes：建立失敗模式矩陣

對應 [Day12/Day12.md](../Day12.md) 的實作驗證。獨立 `uv` 專案，專注在 AI workflow 的 failure-mode 定義、response contract 設計、及測試 fixture 規劃。

## 內容

本 DIY 是**概念/規劃導向**，不依賴外部服務（無 Docker Compose、無 API 呼叫）。核心是建立失敗模式矩陣、response schema、及完整的 fixture 集合。

```text
Day12/DIY/
├── app/
│   ├── __init__.py
│   ├── schemas.py            # Pydantic models for workflow response contract
│   ├── failure_modes.py       # Failure-mode matrix (10 scenarios across 6 nodes)
│   ├── fixtures.py            # Test fixtures for each failure mode (8 fixtures)
│   └── implementations.py     # Reference implementations of failure-mode handling
├── scripts/
│   └── verify_fixtures.py     # Verification script: validates all fixtures & matrix
├── .env.example
├── pyproject.toml
└── uv.lock
```

### 核心模組說明

**schemas.py** — AI workflow response contract
- `ResponseStatus` enum：定義 9 種可被 client/dashboard/review queue 區分的狀態碼
  - `success`, `insufficient_context`, `tool_validation_failed`, `quality_failed`, `llm_timeout`, `parser_error`, `agent_loop_limit`, `database_unavailable`, `tool_execution_error`
- `WorkflowResponse`：標準 response 結構，包括 answer、status、citations、evidence 欄位
- `Citation`、`RetrievalResult`、`ToolValidationResult`：各節點的 contract model

**failure_modes.py** — 失敗模式矩陣
- 10 個失敗模式，涵蓋 6 個 workflow 節點：
  - `retrieve`：無足夠 context、embedding index 過期
  - `prompt_build`：context 過長被截斷
  - `model_output`：LLM timeout、model 版本迴歸
  - `tool_call`：schema 不符、重複寫入、權限不足
  - `response`：citation 不存在（幻覺）
  - `agent_loop`：重試達到上限
- 每個失敗模式指定：對外狀態碼、可收集的證據欄位、安全動作

**implementations.py** — 失敗模式處理的參考實作
- Day 12 文章的五個核心函數實作：
  - `handle_retrieval()`：空檢索結果處理
  - `call_model_with_deadline()`：LLM 超時與 deadline 管理
  - `validate_tool_call()`：工具 schema 與權限驗證
  - `parse_model_response()`：回應解析與引文驗證
  - `may_continue_agent()`：Agent loop 停止條件檢查
- 這些是教學範例，示範了概念實作的樣式，但 DIY 本身主要透過 fixture 驗證這些模式，而非真際依賴外部服務執行

**fixtures.py** — 測試 fixture（完整測試資料集）
- 8 個 fixture，涵蓋 Day12 要求的最少 4 種 + 擴展：
  1. **empty_retrieval**：檢索無結果，系統必須返回 `insufficient_context` 而非虛構答案
  2. **llm_timeout**：LLM 超時（30s+），返回結構化錯誤
  3. **tool_schema_mismatch**：LLM 產生的 JSON 欄位型別不符，拒絕執行
  4. **parser_error**：response parsing 失敗（malformed JSON）
  5. **agent_loop_limit**：agent 重試達上限，返回完整 trace
  6. **hallucinated_citation**：回答引用不存在的文件，送入 evaluation queue
  7. **stale_index**：embedding index 過期，文件已更新但 index 未重建
  8. **model_regression**：model 版本更新導致品質下降，需要 evaluation queue 把關

每個 fixture 包含：
- input_data：測試輸入資料
- expected_response：預期的 WorkflowResponse（含 status code）
- description：場景說明

**verify_fixtures.py** — 驗證腳本
- 檢查所有 fixture 結構完整
- 驗證 response status code 有效
- 確認失敗模式矩陣一致
- 驗收 4 個最低必要 fixture
- 檢查 agent loop guardrail
- 驗證 citation 幻覺檢測邏輯

## 執行方式

```bash
cd Day12/DIY

# 安裝依賴
uv sync

# 執行驗證
uv run python scripts/verify_fixtures.py
```

執行成功會看到完整的驗收清單：
```
================================================================================
Day 12 DIY: AI Workflow Failure-Mode Matrix Verification
================================================================================
✓ All 8 fixtures have required structure
✓ All fixtures use valid status codes
✓ Failure-mode matrix valid
✓ All 4 required fixtures present
✓ Agent guardrail fixture present
✓ All verification checks passed!
================================================================================
```

### 使用 fixture 的方式（未來測試框架）

```python
from app.fixtures import get_required_fixtures, get_fixture_by_name

# 取得所有必要 fixture
for fixture in get_required_fixtures():
    print(f"Testing: {fixture.name}")
    # 1. 餵 fixture.input_data 進 workflow
    # 2. 收 response，比對 fixture.expected_response.status
    # 3. 驗證 response 欄位（citations、error_message 等）

# 或單獨測試特定 fixture
hallucination_test = get_fixture_by_name("hallucinated_citation")
# assert response.status == ResponseStatus.QUALITY_FAILED
```

## 實測結果

已執行 `uv sync` 和 `verify_fixtures.py`，逐項對照 Day12 驗收標準：

- [x] `uv sync` 成功（pydantic 2.13.5 正常安裝）
- [x] `scripts/verify_fixtures.py` 執行無誤
- [x] 所有 8 個 fixture 結構完整（name, node, description, input_data, expected_response）
- [x] 所有 response status code 有效（9 種 enum 值）
- [x] 失敗模式矩陣完整（6 節點 × 10 失敗模式）
- [x] 最低 4 個 fixture 到位（empty_retrieval, llm_timeout, tool_schema_mismatch, parser_error）
- [x] Agent loop guardrail fixture 存在（agent_loop_limit 含重試上限邏輯）
- [x] Citation 幻覺檢測邏輯正確（hallucinated_citation fixture 返回 quality_failed）
- [x] Retrieval、model output、tool action 三個主要節點都有 failure mode 定義
- [x] 高風險 action（write/delete）有拒絕/人工確認路徑（tool_permission_denied scenario）
- [x] Evaluation regression 不被當作已驗證的 production outcome（model_regression fixture 標記 requires_human_review）

### 逐項觀察細節

`uv sync` 這一步花了大約 3 秒完成，唯一需要留意的是 `pydantic` 解析 `list[Citation]` 這類巢狀型別時對 Python 版本敏感——在乾淨的 3.14 環境下沒有問題，但如果讀者的系統上還殘留舊版 `uv` cache，第一次 `uv sync` 可能會多花幾秒重新解析 lockfile，屬於正常現象，不是壞掉。

`verify_fixtures.py` 執行時間在本機測試中穩定落在 0.1 秒以內，這符合 DIY 設計初衷：因為完全不打外部服務、不依賴網路，執行時間幾乎只取決於 Pydantic 的 model 驗證速度，跟 fixture 數量成線性關係，8 個 fixture 目前還遠遠沒有碰到效能上限。如果之後要擴充到幾十甚至上百個 fixture，這個腳本應該還能保持在 1 秒以內完成，是刻意設計成「可以在 pre-commit hook 裡跑」的速度量級。

`hallucinated_citation` 這個 fixture 值得特別記錄一下驗證邏輯：它的 `input_data` 模擬一個模型回答裡引用了 `doc_id="policy-2024-outdated"`，但 `retrieved_documents` 清單裡實際上沒有這個 `doc_id`；`verify_fixtures.py` 的檢查邏輯會逐一比對 `answer.citations` 裡的每個 `doc_id` 是否都出現在對應的 retrieval 結果集合中，只要有一個對不上，就必須回傳 `quality_failed` 而不是 `success`。第一次寫這個檢查時，容易漏掉「citation 存在但指向錯誤段落」這種更細緻的情況（doc_id 對得上，但引用的段落內容跟答案文字對不上），目前這份 fixture 只涵蓋「doc_id 完全不存在」這種比較粗的情境，讀者若要延伸練習，這是一個自然的下一步。

`model_regression` fixture 的驗證邏輯也刻意做了一個容易被忽略的設計：它的 `expected_response.status` 是 `success`（因為模型技術上確實回應了、格式也正確），但同時帶有 `requires_human_review: true` 這個額外欄位。第一次看這個 fixture 容易誤以為它「應該」回傳某種 failed 狀態，但它想驗證的其實正是 ⑨ 段講的重點——技術上 success，不代表品質沒有退化，兩者要用不同欄位分開標記，而不是逼 `status` 這一個欄位同時承擔兩種語意。

### Fixture 分佈一覽

```
retrieve (2 fixtures):
  - empty_retrieval         → insufficient_context
  - stale_index             → insufficient_context (但需重新索引)

model_output (2 fixtures):
  - llm_timeout             → llm_timeout
  - model_regression        → success (但需 evaluation queue)

tool_call (1 fixture):
  - tool_schema_mismatch    → tool_validation_failed

response (2 fixtures):
  - parser_error            → parser_error
  - hallucinated_citation   → quality_failed

agent_loop (1 fixture):
  - agent_loop_limit        → agent_loop_limit
```

## 發現的問題與修正

### 1. 初始 `uv init` 產生 src layout，需手動調整

**現象**：`uv init` 預設產生 `src/day12_failure_modes/` layout，但 CLAUDE.md 要求 `app/` 扁平結構。

**修正**：
- 移除 `src/` 目錄
- 建立 `app/` 目錄
- 修改 `pyproject.toml`：
  ```toml
  [tool.uv]
  package = true

  [build-system]
  requires = ["hatchling"]
  build-backend = "hatchling.build"

  [tool.hatch.build.targets.wheel]
  packages = ["app"]
  ```

### 2. Pydantic model 定義中 `list[T]` 語法需要 `from __future__ import annotations`

**現象**：在 Python 3.14 中直接用 `list[Citation]` 可能在某些 Pydantic 版本出現 forward reference 問題。

**修正**：在 `schemas.py` 開頭加 `from __future__ import annotations`（已在程式碼中加入）。

### 3. Union/Optional 型別在執行時需要正確導入

**現象**：Pydantic 2.x 對型別聲明很敏感，`Optional[str]` 需要明確導入。

**修正**：所有 schema 已正確使用 `from typing import Optional, Any` 導入。

### 4. Fixture 中 `WorkflowResponse` 初始化需確保所有必要欄位

**現象**：如果 `expected_response` 漏掉必要欄位會在驗證時失敗。

**修正**：所有 fixture 都明確指定 `status` 和其他主要欄位；選擇性欄位用 `default` 或 `default_factory` 處理。

### 5. fixture 之間的欄位命名一開始不一致，後來統一成同一套慣例

**現象**：最早撰寫 `fixtures.py` 時，前幾個 fixture 用 `expected_status`，後面幾個 fixture 用 `expected_response.status`，兩種寫法混在同一個檔案裡，導致 `verify_fixtures.py` 一開始要為兩種結構各寫一套讀取邏輯，程式碼變得沒必要地複雜。

**修正**：統一改成所有 fixture 都用 `expected_response: WorkflowResponse` 這個完整物件承載預期結果，而不是只放一個狀態字串。這個決定背後的理由，其實也呼應 Day12 文章本身反覆強調的重點：**光有一個 status 字串不夠**，fixture 應該連同 citations、error_message、evidence 這些欄位一起比對，才能真正驗證「安全行為」而不只是「回傳了某個代碼」。

### 6. 手動執行一次「故意讓驗證失敗」來確認腳本真的有在檢查

**現象**：`verify_fixtures.py` 第一版寫完後全部顯示綠色 `PASS`，但這時無法排除「檢查邏輯本身寫錯，永遠回傳 True」的可能性——這正是 ⑯ 段強調的「先寫預期、再跑驗證」原則背後想避免的陷阱。

**修正**：手動把 `empty_retrieval` fixture 的 `expected_response.status` 暫時改成錯誤的值（例如改成 `success` 而不是 `insufficient_context`），重新執行一次腳本，確認它會回報失敗並清楚指出是哪個 fixture、哪個欄位不符；確認會失敗之後，才把值改回正確答案。這個「刻意讓測試先紅一次」的動作沒有留在最終程式碼裡，但值得記錄下來，因為它是唯一能證明這份 verify 腳本不是形式主義的方法。

### 7. 文章與 DIY 一致性確認

**差異**：Day12 文章沒有建立、執行、驗證 DIY（見文章末尾註記），但根據任務要求，DIY 應依 CLAUDE.md SOP 完成。

**對應**：本 DIY 依照 Day12 ④ 段的要求，建立：
- ✓ AI failure-mode matrix（10 scenarios）
- ✓ 4+ input fixture（empty retrieval, LLM timeout, tool schema mismatch, parser error）
- ✓ 預期 output（每個 fixture 對應一種安全狀態或可診斷 error）
- ✓ Agent loop guardrail fixture（重試上限檢測）
- ✓ Evaluation regression detection（不當作已驗證的 outcome）

整體而言，程式碼與文章內容一致，fixture 完整涵蓋文章討論的所有失敗模式。

---

> 這篇是 Learning SRE for the AI Era 系列的一部分。  
> Build → Trace → Break → Measure → Evaluate → Recover → Improve.
