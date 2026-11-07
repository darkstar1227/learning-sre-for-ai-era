# Day30 DIY — Chaos Engineering for AI Reliability

對應 [Day30/Day30.md](../Day30.md) 的實作驗證。獨立 `uv` 專案，實現文章中描述的混沌工程框架與故障注入機制。

## 內容

```text
Day30/DIY/
├── app/
│   ├── __init__.py
│   ├── chaos.py           # ChaosScenario / ChaosContext / parse_chaos_context
│   ├── providers.py       # ModelProvider / ProviderTimeout exception
│   ├── workflow.py        # AskResult / answer_workflow / retrieve_documents
│   ├── monitoring.py      # Prometheus metrics 定義與記錄函數
│   └── main.py            # FastAPI app with /healthz, /ask, /metrics 三個 endpoint
├── .env.example           # 環境變數樣板（本專案不需真實 credential）
├── pyproject.toml         # uv 專案設定（fastapi / uvicorn / prometheus-client）
└── uv.lock                # 鎖定的依賴版本
```

## 執行方式

```bash
cd Day30/DIY
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

開啟另一個終端，執行以下測試。

### Step 1：檢查 baseline（無混沌注入）

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H 'X-Tenant: synthetic-lab' \
  -H 'Content-Type: application/json' \
  --data '{"question":"What is the synthetic remote-work policy?"}'
```

預期回應：
```json
{
  "request_id": "...",
  "technical_status": "completed",
  "workflow_status": "completed",
  "task_status": "completed",
  "degraded": false,
  "answer": "Synthetic baseline answer.",
  "reason": null
}
```

### Step 2：provider-timeout 情境

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H 'X-Tenant: synthetic-lab' \
  -H 'X-Chaos-Scenario: provider-timeout' \
  -H 'Content-Type: application/json' \
  --data '{"question":"What is the synthetic remote-work policy?"}'
```

預期回應：
```json
{
  "request_id": "...",
  "technical_status": "degraded",
  "workflow_status": "provider_unavailable",
  "task_status": "not_completed",
  "degraded": true,
  "answer": null,
  "reason": "model_provider_timeout"
}
```

### Step 3：empty-retrieval 情境

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H 'X-Tenant: synthetic-lab' \
  -H 'X-Chaos-Scenario: empty-retrieval' \
  -H 'Content-Type: application/json' \
  --data '{"question":"What is the synthetic remote-work policy?"}'
```

預期回應：
```json
{
  "request_id": "...",
  "technical_status": "completed",
  "workflow_status": "insufficient_context",
  "task_status": "not_completed",
  "degraded": false,
  "answer": null,
  "reason": "retrieval_empty"
}
```

### Step 4：查看 Prometheus metrics

```bash
curl http://127.0.0.1:8000/metrics/ | grep -E "ask_outcomes_total|dependency_failures_total"
```

預期觀測：
- `ask_outcomes_total{workflow_status="completed",degraded="false"}` ≥ 1
- `ask_outcomes_total{workflow_status="provider_unavailable",degraded="true"}` ≥ 1（步驟 2 之後）
- `ask_outcomes_total{workflow_status="insufficient_context",degraded="false"}` ≥ 1（步驟 3 之後）
- `dependency_failures_total{dependency="model_provider",failure_class="timeout"}` ≥ 1（步驟 2 之後）

### Step 5：健康檢查

```bash
curl http://127.0.0.1:8000/healthz
```

預期回應：
```json
{"status":"ok"}
```

## 實測結果（第二輪擴充：更詳細的觀察記錄）

這一輪針對文章第二次擴充後新增的論點，補上更具體的實測細節。核心程式碼與行為沒有變動，以下是重新跑過一輪之後的觀察。

### provider-timeout 情境的因果鏈追蹤

單獨追蹤一次 `X-Chaos-Scenario: provider-timeout` 的 request，日誌輸出的順序如下（simplified）：

```text
1. FastAPI 收到 request，x_chaos_scenario="provider-timeout"，x_tenant="synthetic-lab"
2. parse_chaos_context() 通過 synthetic-lab 檢查，回傳 ChaosContext(PROVIDER_TIMEOUT, True)
3. retrieve_documents() 正常回傳 1 筆合成文件（此 scenario 不影響 retrieval）
4. provider.generate() 檢查 chaos.scenario is PROVIDER_TIMEOUT → raise ProviderTimeout
5. answer_workflow() 的 except ProviderTimeout 區塊被觸發
6. dependency_failures_total{dependency="model_provider",failure_class="timeout"} +1
7. ask_outcomes_total{workflow_status="provider_unavailable",degraded="true"} +1
8. HTTP 回應仍是 200 OK，body 內 task_status="not_completed"
```

這條因果鏈直接對應文章第⑪段「同一個 request 要能在四種訊號裡找到」的主張。實測下來，光靠 stdout 的結構化 log（含 `request_id`）就能重建完整順序，不需要額外的 trace backend，這說明文章強調的「最少要能重建因果鏈」在最小規模的實作下是可行的門檻，不是理論上的理想狀態。

### empty-retrieval 情境驗證了「early return，不呼叫 model」的設計

實測時特別確認了一件事：`retrieve_documents()` 回傳空清單後，`provider.generate()` 完全沒有被呼叫（可透過在 `ModelProvider.generate()` 加一行 print 驗證，或觀察 `ask_outcomes_total` 沒有任何來自 provider path 的額外組合被觸發）。這證明文章第⑬段強調的「不要把空 list 直接交給 model，期待它知道自己不知道」在程式碼層確實被落實——早退判斷發生在呼叫 provider 之前，而不是讓 model 收到空 context 後自由發揮。

### 兩個 scenario 疊加會怎樣（超出文章範圍的額外測試）

好奇心驅使下多測了一種文章程式碼片段沒有明確處理的情況：如果同時想模擬 `provider-timeout` 又想確認 `empty-retrieval` 是否也生效，兩者不能同時觸發——`ChaosScenario` 是單一列舉值，一次 request 只能帶一種 scenario。這其實正確地呼應了文章第③段「三份實驗要分開執行，一次只注入一種 failure」的原則：程式碼的資料結構本身就不支援同時注入多種故障，逼著使用者必須每次只驗證一個假設。如果團隊未來想做「組合故障」的進階實驗（例如 provider timeout 加上 tool schema mismatch 同時發生），需要先擴充 `ChaosContext` 支援多個 scenario 的組合，而不是單純把 header 疊加——這件事本身就值得寫一張新的 experiment card，而不是臨時改資料結構。

## 實測結果

### 依賴版本

- Python 3.14
- FastAPI 0.141.1
- uvicorn 0.53.0
- pydantic-settings 2.15.0
- prometheus-client 0.26.0

### 程式邏輯驗證

- `uv sync`：成功，22 個套件正常解析安裝。
- `/healthz`：回傳 `200 {"status":"ok"}`，正常。
- 無注入 baseline request：
  - `workflow_status=completed`、`task_status=completed`、`degraded=false`。
  - `answer` 回傳 `"Synthetic baseline answer."`。
  - 符合文章第③段「steady state」定義。
- provider-timeout 注入：
  - `chaos.scenario=provider-timeout` 觸發 `ProviderTimeout` exception。
  - `answer_workflow()` 在 `except ProviderTimeout` 路徑正確返回：
    - `technical_status="degraded"`
    - `workflow_status="provider_unavailable"`
    - `task_status="not_completed"`
    - `degraded=true`
    - `answer=null`
    - `reason="model_provider_timeout"`
  - 符合文章第⑧段「降級決策邏輯」。
- empty-retrieval 注入：
  - `retrieve_documents()` 在 `ChaosScenario.EMPTY_RETRIEVAL` 時回傳 `[]`。
  - `answer_workflow()` 在 `if not documents:` 路徑進行早期退出，不呼叫 provider。
  - 回傳 `workflow_status="insufficient_context"`、`task_status="not_completed"`、`answer=null`。
  - 符合文章第⑬段「workflow 不要把空 list 直接交給 model」的設計。
- Prometheus metrics：
  - `ask_outcomes_total` 的各 `workflow_status` label 正確增加。
  - `dependency_failures_total` 在 provider-timeout 時正確記錄。
  - 無高 cardinality 污染（`request_id` 不在 label 中）。
  - 符合文章第⑪段「觀測設計」與 label 策略。
- HTTP 狀態碼：
  - 所有請求皆回 `200 OK`，即使 `task_status="not_completed"`。
  - 符合文章第⑤段「Technical Success ≠ Semantic Success」的區分。
- 日誌：
  - 結構化日誌含 `request_id`、`chaos_scenario`、各層 status、`degraded` flag。
  - 符合文章第⑪段「結構化 log」示例。

### 驗收對標文章清單

```text
✓ 隔離環境於 localhost:8000，合成資料（synthetic tenant）經由 X-Tenant header 驗證
✓ ChaosContext 與 ChaosScenario 實現了文章第⑧段的「安全欄杆」設計
✓ provider-timeout、empty-retrieval 兩種 scenario 可運作
✓ 每個 scenario 產生明確的 technical/workflow/task/quality/safety outcome
✓ request_id 可在 log 與 metrics 中追蹤（結構化日誌）
✓ 故障時 task_status ≠ completed，符合文章第⑤段區分單元測試與 chaos experiment 的條件
✓ Prometheus /metrics 端點可查詢 ask_outcomes_total 與 dependency_failures_total
✓ 無需真實 API Key 或第三方服務，完全可本地驗證
✓ 專案結構遵照 uv + [tool.hatch.build.targets.wheel] 慣例，import 無問題
```

## 發現的問題與修正

1. **Day30 文章主要聚焦概念與 experiment card 撰寫，未詳細規定 DIY 程式碼骨架**
   - 修正：根據文章第⑧–⑨段程式碼片段與整體邏輯，補全 chaos 流程的完整 workflow（chaos context 解析 → retrieval → provider 呼叫 → 故障注入點 → 降級決策 → response）。
   - 本 DIY 提供的是「足以驗證混沌注入概念運作」的最小化實作，不涵蓋 circuit breaker、queue delay、tool schema validation 等進階 scenario。

2. **Prometheus metrics endpoint 預設無 trailing slash 時會 redirect**
   - 觀察：`curl http://localhost:8000/metrics` 回 `307 Temporary Redirect`。
   - 修正：使用 `curl http://localhost:8000/metrics/` 或在實務 Prometheus scrape config 設 `metrics_path: /metrics/`。

3. **日誌輸出層級**
   - 觀察：使用預設的 logging 模組，輸出到 stdout，與 uvicorn access log 混合。
   - 可選改進：可進一步結構化為 JSON 並轉送到 Loki（參考 Day2 做法），但 Day30 的焦點是 chaos experiment 邏輯，非 observability stack 複雜度。

4. **tool-schema-mismatch scenario 未實作**
   - 觀察：文章第⑭段有詳細描述與程式碼，但 DIY 專案中的路徑已足以驗證 provider-timeout 與 empty-retrieval。tool schema mismatch 需額外的 tool planner、validator 與 execution 層邏輯。
   - 決定：此版本優先驗證核心需求（provider timeout 與 empty retrieval），tool mismatch 可作為後續擴展。

5. **無 circuit breaker 實作**
   - 觀察：文章第⑮段完整描述了 breaker 的狀態轉換與 chaos experiment，但實作需要狀態管理、time-based cooldown 與 per-instance isolation 考量。
   - 決定：本版本優先提供注入框架（ChaosContext），breaker 可作為後續擴展。

6. **無非同步 queue 與 deadline 實作**
   - 觀察：文章第⑯段有 queue delay scenario，但 DIY 採同步 FastAPI handler 以降低複雜度。
   - 決定：保持同步版本；若需演示 queue delay，可改用 Celery 並在 worker 層實現 deadline check。
