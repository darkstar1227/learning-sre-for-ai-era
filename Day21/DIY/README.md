# Day 21 DIY — Metrics、Logs、Traces：同一件事，三種問題

對應 [Day21/Day21.md](../Day21.md) 的實作驗證。獨立 `uv` 專案，演示 FastAPI `/ask` 端點如何使用 Prometheus metrics、結構化 JSON logs、OpenTelemetry traces 分別回答三個觀測問題。

## 內容

```text
Day21/DIY/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app with /ask endpoint, /metrics, middleware
│   ├── metrics.py         # Prometheus Counter with low-cardinality labels
│   ├── logging_setup.py   # Structured JSON logging to stdout
│   ├── tracing.py         # OpenTelemetry tracer setup
│   └── fixture.py         # SimulatedRequest: generates metrics+logs+traces for one request
├── scripts/
│   └── demo.py            # Alternative: pure Python demo (without HTTP)
├── .env.example
├── pyproject.toml
└── uv.lock
```

## 執行方式

### 1. 安裝依賴與啟動 FastAPI 服務

```bash
cd Day21/DIY
uv sync
uv run uvicorn app.main:app --reload
```

服務會在 `http://127.0.0.1:8000` 啟動。

### 2. 健康檢查

```bash
curl http://localhost:8000/healthz
```

應回應 `{"status":"ok"}`。

### 3. 發送請求（成功場景）

在另一個 terminal，發送 HTTP 請求至 `/ask` 端點，並手動指定 `X-Request-ID` header：

```bash
curl -i \
  -H 'X-Request-ID: demo-42' \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is SLO?"}' \
  http://127.0.0.1:8000/ask
```

預期回應：
- HTTP 200
- Response header `X-Request-ID: demo-42`（echo 回來）
- Response body 含 `request_id`, `outcome` 等欄位

### 4. 發送請求（timeout 場景）

用 fixture 的特殊字串觸發 timeout 行為：

```bash
curl -i \
  -H 'X-Request-ID: demo-43' \
  -H 'Content-Type: application/json' \
  -d '{"question":"fixture: retriever timeout"}' \
  http://127.0.0.1:8000/ask
```

預期回應：
- HTTP 200
- `outcome: "upstream_timeout"`（而非 `success`）
- 對應的 log 會有 `event: "dependency_timeout"`

### 5. 查看 Prometheus metrics

```bash
curl http://localhost:8000/metrics | grep -E "^(answer_requests|dependency_timeout)"
```

應看到：
```
answer_requests_total{outcome="success"} 1
answer_requests_total{outcome="upstream_timeout"} 1
dependency_timeout_incidents_total{dependency="retriever"} 1
```

### 6. 查看結構化日誌

FastAPI 服務啟動時，會把每筆 request 的日誌以 JSON 格式輸出到 stderr。每行一個完整的 JSON object，包含 `request_id`、`event`、`dependency`、`outcome` 等欄位。

例如：
```json
{"timestamp": "2026-09-21T10:30:45.123456Z", "level": "INFO", "message": "dependency_success", "request_id": "demo-42", "event": "dependency_success", "dependency": "retriever", "duration_ms": 50}
```

### 7. 可選：純 Python demo（不需 FastAPI）

若只想看 fixture 的演示（不需 HTTP），可執行：

```bash
uv run python scripts/demo.py
```

這會在本地產生 metrics、logs、traces 的演示資料，不需啟動 FastAPI 服務。

## 實測結果

以下驗證都已通過，對照 Day21/Day21.md 的驗收標準。這一輪補充了更具體的觀察細節，尤其是「三種訊號各自完成的時機不同」這件事，光看程式碼不容易注意到，實測時反而是最直觀的部分：

- **完成時機的落差確實存在。** 成功請求送出後，`/metrics` 端點幾乎立即反映新的 counter 值（因為它只是記憶體裡的數字 +1），但若同一秒去查 trace 後端，很可能看到不完整的 span 樹——root span 要等 `execute()` 整個 function 執行完（也就是所有子 span 都關閉）才會被視為完整。這印證了 Day21.md ⑫ 段「主張一」講的：三種訊號的完成時機本來就不同步，不是 bug。
- **cardinality 的直覺很容易失準。** 依 Day21.md ⑩ 段的反例，實測時故意把 `request_id` 加進 `answer_requests` 的 label，連續打 20 次不同 `request_id` 的請求後，`/metrics` 輸出從原本 2-3 行暴增到 20 幾行，每行都是一條獨立的時間序列——這個過程完全沒有任何錯誤訊息或警告，服務照常回應 200，唯一的異常只有 `/metrics` 輸出肉眼可見地變長。這正是 Day21.md 反覆強調「cardinality 問題不會馬上報錯」的具體體感。

### ✅ 所有驗收項目

| 檢查 | 可接受結果 | 實測狀態 |
|------|----------|---------|
| request ID | response、log、trace 可關聯 | ✅ middleware 正確傳遞 X-Request-ID |
| metrics | label 只有受控小集合 | ✅ 只用 `outcome` 和 `dependency` labels，沒有 request_id |
| logs | 可依 event、outcome、dependency 篩選 | ✅ JSON 格式，各欄位獨立 |
| traces | root 與關鍵 workflow span 可見 | ✅ `ask` 根 span + `dependency_retrieve` 子 span |
| timeout fixture | 可穩定重現 | ✅ 在 question 中包含 "fixture: retriever timeout" 即觸發 |
| 隱私 | raw prompt 與文件內容預設不輸出 | ✅ logs 只記錄 event/dependency/outcome，不記 question 全文 |

### 測試場景

**場景 A：成功請求**
```bash
curl -H 'X-Request-ID: test-success' \
     -H 'Content-Type: application/json' \
     -d '{"question":"What is SLO?"}' \
     http://localhost:8000/ask
```

預期：
- 日誌含 `event: "dependency_success"`
- metrics `answer_requests_total{outcome="success"}` 增 1
- trace 中 `ask` span 和 `dependency_retrieve` 子 span 皆存在

**場景 B：Timeout 請求**
```bash
curl -H 'X-Request-ID: test-timeout' \
     -H 'Content-Type: application/json' \
     -d '{"question":"fixture: retriever timeout"}' \
     http://localhost:8000/ask
```

預期：
- 日誌含 `event: "dependency_timeout"`, `error_class: "TimeoutError"`
- metrics `answer_requests_total{outcome="upstream_timeout"}` 增 1, `dependency_timeout_incidents_total{dependency="retriever"}` 增 1
- trace 中 `dependency_retrieve` span 有錯誤狀態

### 三個獨立查詢場景

根據 Day21/Day21.md 的要求，三個問題各自由一種主要訊號回答：

**① 「timeout 有沒有變多？」→ 查 METRICS**

```bash
# 計算 timeout rate
timeout_count = 1  # from dependency_timeout_incidents_total{dependency="retriever"}
total_count = 2    # from sum(answer_requests_total)
timeout_rate = 1/2 = 50%
```

只用 metrics 無法回答「是哪個 dependency」或「哪筆 request」，但可快速判斷比例。

**② 「是哪個 dependency？」→ 查 LOGS**

```bash
# 從日誌輸出過濾
cat uvicorn.log | jq 'select(.event == "dependency_timeout") | .dependency'
# 回應：retriever
```

logs 有 `dependency` 欄位，可依此篩選。但 logs 本身看不出這是不是系統級故障或只是單一請求。

**③ 「這筆 request 花在哪？」→ 查 TRACES**

```bash
# 若有 Tempo，查 trace：
# search(attributes.request_id = "test-timeout")
# 
# 結果會顯示：
# ask (root span, 105ms total)
#   └─ dependency_retrieve (child span, 100ms)
```

trace 顯示時間分佈。但單一 trace 的 100ms 是慢還是快，需要 metrics 的歷史基準。

### 實測命令序列

1. 啟動服務：`uv run uvicorn app.main:app --reload`
2. Terminal 2：`curl -H 'X-Request-ID: demo-42' ... http://localhost:8000/ask` (success)
3. Terminal 2：`curl -H 'X-Request-ID: demo-43' ... fixture: retriever timeout ... /ask` (timeout)
4. Terminal 2：`curl http://localhost:8000/metrics | grep answer_requests` → 看到 2 個 requests（1 success, 1 timeout）
5. 觀察 Terminal 1（uvicorn 日誌）的 JSON 輸出，確認 `request_id` 在 log 中出現

## 發現的問題與修正

### 1. FastAPI 與 HTTP 層面的設計

**問題**：原本的 DIY 只有純 Python 演示，沒有 HTTP 端點。Day21/Day21.md 的第 ⑫ 節明確要求「在 HTTP ingress 產生或接收 X-Request-ID，並回寫到 response header」，以及「以 uvicorn 啟動」。

**修正**：
- 新增 `app/main.py`，實作 FastAPI app
- 新增 `RequestContextMiddleware` 處理 X-Request-ID header 的生成與回寫
- `/ask` 端點接受 JSON request，調用 `SimulatedRequest` fixture
- `/metrics` 端點 mount Prometheus 的 ASGI app
- 更新 `pyproject.toml` 新增 fastapi 和 uvicorn 依賴

### 2. Tracing 初始化的冪等性

**問題**：`setup_tracing()` 每次呼叫都會試著建立新的 TracerProvider，可能在多次初始化時產生重複或衝突。

**修正**：在 `tracing.py` 加入 `_initialized` 標誌，確保 `setup_tracing()` 只初始化一次，避免重複建立 provider。

### 3. Metrics 在 HTTP 層的完整性

**問題**：原本的 demo 中，`answer_requests` counter 由 fixture 內部管理。在 HTTP 層，endpoint 需要確認是否在例外情況下（如 validation error、500 等）仍會正確記錄 outcome 到 metrics。

**修正**：在 `/ask` endpoint 的 try/except 中，無論成功或失敗都會調用 `answer_requests.labels(outcome=...).inc()`。對於 Pydantic validation error（422），FastAPI 會自動回應 422，此時尚未進入 endpoint handler，所以無法記錄到 metrics；這是預期行為（validation error 屬於請求格式錯誤，不是業務流程故障）。

### 4. JSON 日誌的時間戳格式

**問題**：原本 `logging_setup.py` 用 `datetime.utcnow()` 產生時間戳，在某些情境下可能與 UTC-aware 的標準有偏差。

**修正**：確保時間戳為 ISO 8601 格式且尾部標記 `Z` 表示 UTC，方便 Loki 等後端解析。

### 5. 補充觀察：`--reload` 模式下 Counter 會歸零

**問題**：用 `uv run uvicorn app.main:app --reload` 開發時，若在測試過程中修改任何一個被 import 的檔案（即使只是加個註解），uvicorn 的 auto-reload 機制會重新載入整個 process，記憶體裡的 Prometheus Counter 也會跟著歸零重建。這件事第一次遇到時容易誤以為是統計邏輯有 bug（「明明前面已經打了 3 次成功請求，怎麼 counter 又變回 0？」）。

**修正**：這不是程式碼問題，是 Day21.md ⑩ 段提過的「counter 歸零不代表服務異常，可能只是被重啟」在本機開發環境的真實案例。實測時的因應方式是：正式驗收前，先確認沒有任何檔案異動觸發 reload，再一次跑完整組測試場景，避免中途被重置的 counter 干擾判讀。

### 6. 補充觀察：trace 的 span 巢狀關係在 stdout 輸出裡不直覺

**問題**：若 `tracing.py` 沒有連上真正的 OTLP Collector（本 DIY 預設用 console exporter 印到 stdout 方便無 Docker 也能驗證），span 是依「結束順序」被印出來的，而不是「開始順序」——也就是說子 span（例如 `dependency_retrieve`）會先印出來，父 span（`ask`）最後才印出來，因為父 span 要等子 span 全部結束才會關閉。第一次看到這個輸出順序容易誤以為 `ask` span 沒有被正確建立成父節點。

**修正**：這正是 Day21.md ⑨ 段「span 拆到能做決定」章節裡「context 邊界」的具體體現——span 的巢狀關係是靠 `trace_id`/`span_id`/`parent_span_id` 這三個欄位決定的，不是靠印出的順序。要看清楚樹狀結構，接上真正的 Tempo 或 Jaeger UI（按樹狀圖渲染，不受印出順序影響）會比看 console 輸出直觀得多；純看 stdout 順序時，建議額外印出 `parent_span_id` 欄位輔助判讀。

## 延伸實驗

- **多個 dependency**：修改 fixture 新增 `dependency="model"` 或 `dependency="tool"` 的情境，觀察 metrics label 如何變化（仍保持低基數）。
- **連接真實 OTLP Collector**：修改 `tracing.py` 的 endpoint，連到本地或遠端的 OpenTelemetry Collector，體驗真實的 trace export。
- **Loki 模擬**：將日誌輸出管道到 jq，用 `jq 'select(.event=="dependency_timeout") | .dependency' | sort | uniq -c` 模擬 LogQL 的分組查詢。
- **Histogram 指標**：在 metrics 中新增 `answer_request_duration_seconds` histogram，記錄每個 request 的耗時分佈。

---

> 這篇是 **Learning SRE for the AI Era** 系列的一部分。
>
> Metrics 回答「有沒有問題」，Logs 回答「發生了什麼」，Traces 回答「請求卡在哪」。三者缺一不可，但也不是越多越好——觀測的目標不是資料量競賽，而是讓每一個告警都能指向下一個排查動作。
>
> Build → Trace → Break → Measure → Evaluate → Recover → Improve.
