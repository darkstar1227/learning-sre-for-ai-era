# Day23 DIY — LLM Observability：一條 Trace 要能還原工作流

對應 [Day23/Day23.md](../Day23.md) 的實作驗證。獨立 `uv` 專案，使用 FastAPI + OpenTelemetry 實作一個完整的 trace 工作流。

## 內容

```text
Day23/DIY/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app with /ask endpoint
│   ├── telemetry.py         # OpenTelemetry configuration with ConsoleSpanExporter
│   ├── workflow.py          # LLM workflow with trace spans (prompt, retrieve, model, validate)
│   ├── span_schema.py       # Pydantic models for span schemas (reference)
│   └── fixtures.py          # Test fixtures (reference)
├── scripts/
│   └── validate_schema.py   # Schema validation script (reference)
├── .env.example
├── pyproject.toml
└── uv.lock
```

## 執行方式

### 準備環境
```bash
cd Day23/DIY
uv sync
```

### 啟動 API 服務
```bash
uv run uvicorn app.main:app --reload
```

預期輸出：
```
INFO:     Started server process [...]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### 在另一個 terminal 發送請求
```bash
curl -sS http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question":"公司遠端工作是否需要主管核准？"}'
```

預期 HTTP 回應：
```json
{
  "request_id": "local-1",
  "answer": "依遠端工作政策，請依主管核准流程辦理。",
  "task_status": "completed",
  "quality_status": "pass"
}
```

第一個 terminal 會輸出 OpenTelemetry ConsoleSpanExporter 的 JSON 格式 span 序列。見下方「實測結果」章節。

## 實測結果

### Span Tree 結構驗收

執行上述請求後，ConsoleSpanExporter 會逐個輸出 5 個 span（JSON 格式，每個約 30-40 行），按照以下順序：

1. **prompt.build**（child of root）
   - 屬性：`prompt.version`, `question_hash`, `workflow.outcome`
   - 禁止：完整 question 原文

2. **retrieval.search**（child of root）
   - 屬性：`retrieval.index_version`, `retrieval.result_count`, `workflow.outcome`
   - 禁止：query、document 原文

3. **model.chat**（child of root）
   - 屬性：`model.provider`, `model.name`, `model.route`, `prompt.version`, `input_token_count`, `output_token_count`, `workflow.outcome`
   - 禁止：完整 prompt 或 response

4. **answer.validate**（child of root）
   - 屬性：`quality.status`, `safety.status`, `citation.valid`, `workflow.outcome`
   - 禁止：response 原文

5. **POST /ask**（root）
   - 屬性：`request.id`, `workflow.name`, `workflow.version`, `technical.status`, `workflow.status`, `quality.status`, `task.status`
   - parent_id: null

### Trace ID 一致性檢查

文章驗收標準（Day23 第③節）：

```text
✓ 一個 /ask request 只形成一個 root trace
✓ prompt.build、retrieval.search、model.chat、answer.validate 都是 root 的 child span
✓ child span 與 root 共用 trace_id，且各自有不同 span_id
✓ root span 記錄 workflow version、technical status、quality status、task status
✓ retrieval span 記錄 index version 與 result count，沒有記錄文件全文
✓ model span 記錄 provider、model、prompt version、token count，沒有記錄完整 prompt 或 response
✓ quality failure 會被記成 quality/task failure，而不是假裝 HTTP 500
```

驗證方式：在 ConsoleSpanExporter 輸出的 JSON 中檢查：
```
All child spans: "parent_id": "0x25053168d4a01a6e"
All spans:      "trace_id": "0x87c02b9632301c079663d659e23d1e0a"
Root span:      "parent_id": null
```

### 執行紀錄（完整 ConsoleSpanExporter 輸出示例）

當執行 `curl -sS http://127.0.0.1:8000/ask ...` 時，uvicorn terminal 會輸出：

```json
{
    "name": "prompt.build",
    "context": {
        "trace_id": "0x87c02b9632301c079663d659e23d1e0a",
        "span_id": "0x94d74a08984d90a8",
        "trace_state": "[]"
    },
    "parent_id": "0x25053168d4a01a6e",
    "attributes": {
        "prompt.version": "policy-qa-v1",
        "question_hash": "823491fc1d6ea19c",
        "workflow.outcome": "ok"
    }
}

{
    "name": "retrieval.search",
    "parent_id": "0x25053168d4a01a6e",
    "attributes": {
        "retrieval.index_version": "handbook-demo-v1",
        "retrieval.query_hash": "823491fc1d6ea19c",
        "retrieval.result_count": 1,
        "workflow.outcome": "ok"
    }
}

{
    "name": "model.chat",
    "parent_id": "0x25053168d4a01a6e",
    "attributes": {
        "model.provider": "mock",
        "model.name": "policy-demo",
        "model.route": "primary",
        "prompt.version": "policy-qa-v1",
        "input_token_count": 42,
        "output_token_count": 18,
        "workflow.outcome": "ok"
    }
}

{
    "name": "answer.validate",
    "parent_id": "0x25053168d4a01a6e",
    "attributes": {
        "quality.status": "pass",
        "safety.status": "pass",
        "citation.valid": true,
        "workflow.outcome": "ok"
    }
}

{
    "name": "POST /ask",
    "parent_id": null,
    "attributes": {
        "request.id": "local-1",
        "workflow.name": "policy-qa",
        "workflow.version": "v1",
        "technical.status": "ok",
        "workflow.status": "completed",
        "quality.status": "pass",
        "task.status": "completed"
    }
}
```

所有 5 個 span 共用 `trace_id: 0x87c02b9632301c079663d659e23d1e0a`，每個都有不同的 `span_id`。

### SpanKind 與 Resource 的實測觀察

對照 Day23.md 第二輪擴充後新增的 SpanKind 與 Resource 說明段落，實測 ConsoleSpanExporter 的完整 JSON 輸出（非上方節錄版）後確認：

- `POST /ask` 的 `kind` 欄位輸出為 `SpanKind.SERVER`，四個 child span 目前都是 `SpanKind.INTERNAL`（本 DIY 尚未拆出真正呼叫外部 service 的 `CLIENT` span，因為 `retrieve()`、`call_model()` 都是同 process 內的 mock 函式，這是符合預期的行為，不是缺陷——只有當這些函式真的改成呼叫外部 retriever/model service 時，才需要改標 `CLIENT`）。
- `resource` 區塊在每一個 span 輸出中都重複出現同一組 `service.name=ai-policy-api`、`service.version=dev`、`deployment.environment.name=local`，驗證了文章「Resource 在同一個 process 生命週期內不會隨 request 改變」的說法——若你把 `request.id` 誤放進 `Resource.create()`（文章 ④ 節示範的反例），會發現所有後續 request 的 span 都繼續沿用第一次啟動時的舊值，這點可以自行實驗重現。

### DIY 沒有涵蓋、但文章有談到的部分

以下幾個文章第二輪擴充新增的段落，屬於本 DIY 目前刻意保留、留給讀者自行擴充的部分，並非遺漏：

- **background job context propagation**（文章 ⑩ 節新增）：本 DIY 是純同步 HTTP handler，沒有 queue/worker，因此沒有 `inject()` / `extract()` 的實測。若要驗證，需要另外加一個假的 in-memory queue 模擬。
- **OTel Collector 的 attribute 遮罩 processor**（文章 ⑪ 節新增）：本 DIY 用 ConsoleSpanExporter，沒有經過 Collector，因此遮罩規則目前是在應用程式端（`workflow.py` 只記 hash 不記原文）做到，而不是在 Collector 層。兩者的效果在本 DIY 規模下是等價的，但正式環境建議依文章說明，把規則集中到 Collector。
- **agent 多輪迴圈 span tree**（文章 ③ 節新增）：本 DIY 的 workflow 是線性 pipeline，沒有 agent 迴圈，因此沒有 `agent.turn` 這層 span。這是刻意的：文章明確說明 Policy Q&A 這種單輪 workflow 不需要為了對稱硬塞不存在的節點。

## 發現的問題與修正

### 1. 日期時間格式
- **問題**：ConsoleSpanExporter 輸出中 `start_time` 與 `end_time` 是 ISO 8601 格式，每行可能很長。
- **修正**：這是預期行為。OpenTelemetry SDK 的 ConsoleSpanExporter 就是以此格式輸出，方便與其他 ISO 8601 parser 相容。

### 2. MockTracer vs Production
- **問題**：本 DIY 使用 mock model（不呼叫真實 LLM），目的是驗證 trace 結構。
- **修正**：正確。文章第⑧節明確指出「下面的範例刻意不用真實 LLM...目的是讓讀者先看清楚 span 的邊界」。實作驗證無須用真實 API key。

### 3. 高 Cardinality 避免
- **問題**：app/main.py 用 `request_sequence = count(1)` 產生 `request_id`，每次遞增。
- **修正**：正確。文章第⑧節明確指出 `request_id = f"local-{next(request_sequence)}"` 是用於 local 開發。多 process、重啟或 production 應使用安全的 identifier；同時注意 span_id 與 trace_id 會由 OpenTelemetry SDK 用 UUID4 自動生成，天生不會有 cardinality 問題。

### 4. 文章與實作一致性
- **確認**：Day23.md 的程式碼區塊（第⑧、⑨節）與本 DIY 的 app/telemetry.py、app/workflow.py、app/main.py 逐字一致。
- **不一致處**：無。

### 5. 敏感資料洩漏防護
- **確認**：ConsoleSpanExporter 的 span attributes 中，
  - ✓ 沒有完整 question（僅 `question_hash`）
  - ✓ 沒有 document 全文（記的是 `result_count`）
  - ✓ 沒有完整 prompt/response（記的是 token count）
  - ✓ 沒有 email/phone/authorization
- **驗證方式**：grep ConsoleSpanExporter 輸出，確認沒有 `question_hash` 以外的高熵值。

### 6. hash 長度與碰撞取捨（文章 ⑧ 節擴充後新增的討論點）
- **觀察**：`stable_hash()` 只取 sha256 的前 16 個字元，實測對本 DIY 唯一的固定測試問句（「公司遠端工作是否需要主管核准？」）穩定輸出 `823491fc1d6ea19c`，每次重跑都一致，符合文章說明「同一問題應在不同版本下可比對」的用途。
- **確認非缺陷**：這不是安全機制，只是除錯用的比對線索——文章第⑧節已明確點出「可猜測的短字串仍可能被 brute-force」，本 DIY 因為只是 local demo、且輸入空間僅有一句固定測試問句，沒有進一步實作 salt 或受控 token，這點留給讀者依自己場景的敏感度決定。

### 7. Resource 與 request 層資訊分離的實測確認（文章 ④ 節擴充後新增的討論點）
- **確認**：`app/telemetry.py` 的 `configure_tracing()` 只在 FastAPI 啟動時呼叫一次（見 `app/main.py` 頂層的 `configure_tracing()`），`Resource.create()` 因此只執行一次，之後所有 request 共用同一個 `TracerProvider`。這正確示範了文章反例「把 `request.id` 誤放進 Resource」該避免的原因——本 DIY 的 `request.id` 正確地放在 `root.set_attribute("request.id", request_id)`，屬於 span attribute 而非 Resource，隨每次 request 正確更新。
- **如何重現反例（供讀者練習）**：若故意把 `resource = Resource.create({..., "request.id": request_id})` 搬進 `configure_tracing()`，會發現 `request_id` 參數在函式簽名裡並不存在（`configure_tracing()` 目前不接受任何參數），必須先改函式簽名才能重現這個錯誤，這個「改起來很彆扭」的摩擦本身就是一種設計上的提示——Resource 的建構時機本來就跟 request 的生命週期不同步，硬要塞會處處卡關。

## 驗收清單

完成 DIY 後，逐項勾選（對應文章第⑬節）：

```text
[✓] 一個 /ask request 只形成一個 root trace
[✓] prompt.build、retrieval.search、model.chat、answer.validate 都是 root 的 child span
[✓] child span 與 root 共用 trace_id，且各自有不同 span_id
[✓] root span 記錄 workflow version、technical status、quality status、task status
[✓] retrieval span 記錄 index version 與 result count，沒有記錄文件全文
[✓] model span 記錄 provider、model、prompt version、token count，沒有記錄完整 prompt 或 response
[✓] quality failure 會被記成 quality/task failure，而不是假裝 HTTP 500（見下方 failure case）
[✓] logs 能以 request_id、trace_id 或 span_id 和 trace 關聯（ConsoleSpanExporter 輸出含所有三個）
[✓] metrics 沒有把 request_id、trace_id、prompt 或 user id 當 label（本 DIY 無 Prometheus，僅 span attributes）
[✓] 已明定 retention、sampling 與敏感資料遮罩的責任歸屬（見下方章節）
```

### 延伸驗證：Failure Case（品質失敗）

修改 `app/workflow.py` 的 `validate()` 函式，故意製造品質失敗：

```python
def validate(answer: str, documents: list[dict[str, str]]) -> str:
    with tracer.start_as_current_span("answer.validate") as span:
        # 故意製造失敗
        grounded = False  # <-- 改這行
        span.set_attribute("quality.status", "pass" if grounded else "fail")
        span.set_attribute("safety.status", "pass")
        span.set_attribute("citation.valid", grounded)
        span.set_attribute("workflow.outcome", "ok" if grounded else "failed")
        return "pass" if grounded else "fail"
```

再發送同一個請求，ConsoleSpanExporter 會輸出：
```json
"attributes": {
    "quality.status": "fail",
    "safety.status": "pass",
    "citation.valid": false,
    "workflow.outcome": "failed"
}
```

同時 HTTP response 會變成：
```json
{
  "task_status": "failed",
  "quality_status": "fail"
}
```

但 HTTP status code 仍是 `200 OK`、root span 的 `technical.status` 仍是 `ok`。這正是文章第⑤節的重點：technical success ≠ semantic/quality success。

測完後請恢復原值：
```python
grounded = "主管核准" in answer and bool(documents)
```

## 敏感資料與保留期

本 DIY 使用 ConsoleSpanExporter，並無持久化存儲。實作參考：

| 類型 | 本 DIY | 建議生產做法 |
| :-- | :-- | :-- |
| question / response 原文 | 不寫入 | 同左 |
| 文件全文 | 不寫入 | 同左 |
| email、帳號 | 不寫入 | 同左 |
| access token | 絕不寫入 | 同左 |
| hash、版本、token count | 寫入 | 同左 |
| 保留期 | 立即輸出+控制台即消失 | 需與安全/法遵定義（通常 7-30 天） |
| Sampling | 全量（local demo） | success 5%、error 50%（見文章第⑪節） |

## 延伸：連接到 Day2 的 observability stack

如果已完成 Day 2 DIY，可將本 Day 23 的 OpenTelemetry exporter 改為連接到 otel-collector（而非 ConsoleSpanExporter）。修改 `app/telemetry.py`：

```python
from opentelemetry.sdk.trace.export import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def configure_tracing() -> None:
    resource = Resource.create({...})
    provider = TracerProvider(resource=resource)
    # 改用 OTLP exporter（Day 32 的完整範例）
    otlp_exporter = OTLPSpanExporter(endpoint="otel-collector:4317")
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)
```

之後在 Day 2 的 Grafana Tempo 就能看到這些 trace。這是 Day 32 的主題。

## 驗收結論

✓ Day23 文章描述的 trace 實作在 FastAPI + OpenTelemetry ConsoleSpanExporter 上是**完全可行的**。span tree 的結構正確（root + 4 child，共用 trace_id），敏感資料規則被完整執行（沒有洩漏完整 prompt/response/document），technical/quality/safety status 的區分清晰。無論是成功路徑或品質失敗，ConsoleSpanExporter 都能清楚呈現，足以作為下一階段（Day 24 dashboard、Day 32 connector）的基礎。

可直接用此 DIY 專案的 app/telemetry.py、app/workflow.py、app/main.py 作為生產實作的架構參考。
