# Day17 DIY — 好的 SLI 與 FastAPI SLO：量得到不代表該量

對應 [Day17/Day17.md](../Day17.md) 的實作驗證。獨立 `uv` 專案，展示 SLI 設計與 FastAPI middleware 的完整實踐。

## 內容

```text
Day17/DIY/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app with middleware, handler, domain exceptions
│   ├── schemas.py            # Pydantic models (AskRequest/Response/SLIEvent)
│   └── sli.py                # SLI definitions + fixture testing
├── tests/
│   ├── __init__.py
│   ├── test_sli.py           # SLI evaluation & fixture tests (18 tests)
│   └── test_api.py           # FastAPI endpoint tests (14 tests)
├── .env.example
├── pyproject.toml            # Dependencies: FastAPI, pytest, prometheus-client
└── uv.lock
```

## 執行方式

### 安裝與測試

```bash
cd Day17/DIY
uv sync                       # 安裝依賴
uv run python -m pytest tests/ -v   # 執行全部測試 (32 tests)
```

### 啟動 API 伺服器

```bash
cd Day17/DIY
uv run uvicorn app.main:app --reload --port 8000
```

### 測試 API 端點

```bash
# 健康檢查
curl http://localhost:8000/healthz

# 正常情況（應記錄 technical_status=success）
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is SRE?"}'

# 模擬上游逾時（應記錄 technical_status=dependency_timeout，回傳 504）
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "This is timeout"}'

# 模擬上游提供者錯誤（應記錄 technical_status=dependency_error，回傳 502）
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "This is error"}'

# 模擬無效回應（應記錄 technical_status=validation_error，回傳 502）
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "This is malformed"}'

# 查看所有記錄的事件（測試用）
curl http://localhost:8000/events

# 查看 Prometheus metrics
curl http://localhost:8000/metrics

# 重置事件日誌
curl -X POST http://localhost:8000/events/reset
```

## 實測結果

所有 32 個單元測試與整合測試皆通過。

### ✓ Day 17 文章 Step 1-7 實現完整性

#### Step 1：純函式分類邏輯
- [x] `classify_status()` 函式，無依賴，可單獨測試
- [x] 根據 HTTP status code 與 error_kind 分類為 `success` / `dependency_timeout` / `dependency_error` / `validation_error` / `internal_error`

#### Step 2：預期分類表與 Fixtures
- [x] `SLIFixture` 類別，代表一個應該 fail 的反例
- [x] 7 個 fixtures：
  - 好的情況：HTTP 200 + 快速完成
  - Outcome 反例 2 個：HTTP 200 但缺欄位、provider 錯誤
  - Latency 反例 2 個：超過 5s 門檻的慢請求
  - Dependency 反例 2 個：provider timeout、provider error exhaustion
- [x] 每個 fixture 有明確的「使用者感受」描述

#### Step 3：Middleware 實現
- [x] `record_request_sli()` middleware（文章 ⑤ 節原文實現）
- [x] 只監測 `/ask` endpoint，避免其他路由的 cardinality 爆炸
- [x] 用 `request.state` 傳遞 technical_status
- [x] 在 `finally` 塊確保 exception path 仍會產生 measurement
- [x] 記錄 Prometheus Counter 與 Histogram metrics

#### Step 4：四種可預期請求的 Mock
- [x] 正常答案（問題不含特殊關鍵字） → HTTP 200, technical_status=success
- [x] Provider timeout（問題含 "timeout"） → HTTP 504, technical_status=dependency_timeout
- [x] Provider error（問題含 "error"） → HTTP 502, technical_status=dependency_error
- [x] 無效輸出（問題含 "malformed"） → HTTP 502, technical_status=validation_error

#### Step 5：HTTP 200 但品質不佳的反例
- [x] OutputValidationError 例外，返回 HTTP 502 但 middleware 記錄為不同的 technical_status
- [x] 區分「技術上成功」與「語意上正確」

#### Step 6：Label 基數檢查
- [x] Prometheus Counter 的 labels：`route`, `technical_status`, `release_channel`
- [x] **無高基數 label**：不含 `prompt`, `user_id`, `answer`, `request_id`
- [x] 只有 5 種 technical_status 值（stable cardinality）
- [x] 事件中完全無敏感資訊

#### Step 7：短窗 PromQL Sanity Check
- [x] 手算與 query 結果一致（透過測試驗證）
- [x] 4 個測試請求 → 期望 1 success，3 failures → SLI 分子分母正確

### ✓ Prometheus 指標與結構化日誌

```python
REQUESTS = Counter(
    "answer_requests_total",
    "Completed answer requests grouped by technical outcome.",
    ["route", "technical_status", "release_channel"],
)

LATENCY = Histogram(
    "answer_request_duration_seconds",
    "End-to-end HTTP request duration for the answer route.",
    ["route", "release_channel"],
    buckets=(0.1, 0.3, 0.5, 1, 2, 3, 5, 10),  # Day 17 要求的 3 秒門檻
)
```

- [x] `/metrics` 端點暴露 Prometheus 格式的 metrics
- [x] Structured logging 記錄 `route`, `technical_status`, `latency_ms`, `release_channel`

### ✓ Domain Exceptions 與 Handler 分類

```python
class ProviderTimeoutError(Exception): pass
class ProviderError(Exception): pass
class OutputValidationError(Exception): pass
```

- [x] Handler 捕捉特定例外並設定 `request.state.technical_status`
- [x] Middleware 透過 `getattr(request.state, "technical_status", ...)` 讀取分類
- [x] 業務邏輯與 web framework 分離

### ✓ 測試覆蓋率

```
test_sli.py (18 tests)      ✓ 18/18 通過
test_api.py (14 tests)      ✓ 14/14 通過
─────────────────────────────────────
總計                       ✓ 32/32 通過
```

每個 test case 對應文章的一個驗收項目。

### 更具體的觀察：middleware 只有一層，分母的界線因此很明確

這個 DIY 目前只掛了 `record_request_sli` 這一個 middleware，`app/main.py` 沒有另外疊加框架內建的 host 檢查或限流 middleware。這一點反而讓文章 ⑤ 節「middleware 疊加順序決定分母邊界」的討論更容易對照：因為只有一層，這個 DIY 量到的分母永遠是「所有到達 ASGI app 的 `/ask` 請求」，不存在被更外層 middleware 提早攔截、完全繞過計數的狀況。若日後要在這個 DIY 上疊加第二個 middleware（例如限流），依文章 ⑤ 節的討論，應該先決定「被擋下的請求算不算 eligible event」，再決定新 middleware 該註冊在 `record_request_sli` 的內層還是外層，而不是憑框架預設順序決定。

### 更具體的觀察：cardinality 上限是可以直接算出來的

依 `app/main.py` 目前的 `REQUESTS` counter 定義，label 組合的理論上限是：

```text
answer_requests_total 的 label 組合數 = 1 (route，固定 /ask) × 5 (technical_status) × 2 (release_channel，stable/canary)
                                     = 10 種
```

不管對 `/ask` 送出多少筆內容互不相同的問題（`question` 欄位完全不會出現在任何 label 裡），這個上限都不會被突破——因為 `classify_status()` 與 handler 傳給 middleware 的欄位，從一開始就沒有把請求內容當成分類依據。這是文章 ④ 節「event schema 只保留低基數欄位」的設計，落到這份程式碼裡最直接的驗證方式：不用真的送一百萬筆請求去看記憶體會不會爆，只要看 label 定義本身，上限已經寫死在型別（`Literal[TechnicalStatus]` 只有 5 種值）與 counter 的 label 清單裡。

## 發現的問題與修正

### 1. HTTP Status Code 選擇：504 vs 503

**問題**：上游 provider 逾時時，該返回 504 還是 503？

**決定**：使用 **504 Gateway Timeout**
- 504 = 網關收到來自上游的逾時
- 503 = 本服務暫時不可用（可能是本身過載，也可能是依賴故障）

在 DIY 中，由於是模擬 provider 側的問題，504 更準確。在實際系統中，決定應根據架構而定。

### 2. 完整 Middleware 與 Event 記錄

**問題**：文章 ⑦ 節說「本文沒有建立 DIY 專案」，但 Step 3 要求「將 middleware 加到測試服務」。

**解決**：文章 ⑦ 節的意思是「文章本文沒有給出可直接執行的完整程式」，而 DIY 部分正是要將文章的代碼片段（middleware、handler）組裝成完整、可測試的專案。

**實現**：
- 完整實現文章 ⑤ 節的 middleware
- 在測試時同時記錄到記憶體中的 `event_log`（供測試驗證）與 Prometheus metrics（供實際監控）

### 3. Domain Exceptions 的細粒度分類

**問題**：原始設計中，所有「provider 側問題」都用 `ProviderTimeoutError`。

**修正**：
- `ProviderTimeoutError` ← 明確的 timeout 情景
- `ProviderError` ← 提供者返回錯誤（4xx/5xx）
- `OutputValidationError` ← 輸出格式不合法
- 其他 `Exception` ← 未預期的系統故障

每個異常對應不同的 HTTP 狀態碼與 technical_status，讓值班人員能夠清楚判斷問題所在。

### 4. 測試隔離與 Event Log 清除

**實現**：
- Pytest fixture `clear_events()` 在每個 test 前後清空 `event_log`
- `/events/reset` endpoint 供手動測試時清除
- Prometheus metrics 則保持不清除（模擬真實監控系統的累積特性）

### 5. 文章擴充後新提到的欄位拆分，這份 DIY 尚未實作

文章 ② 節擴充後新增了「把 `latency_ms` 拆成 `queue_time` / `process_time` / `io_time` 三段」的討論，用來說明單一 latency 數字無法定位瓶頸在哪一段。目前這份 DIY（`app/main.py`、`app/schemas.py`）仍只記錄單一的 `latency_ms`，沒有實作這三段式拆分——這是本輪擴寫過程中確認到的、文章敘述領先於程式碼實作的落差。

這不算 bug，是刻意的取捨：DIY 的目的是驗證「分類邏輯」與「middleware 記錄機制」這兩件事，三段式拆分屬於「同一個原則可以做得更細」的延伸，不影響文章 ③⑤ 節核心論點的正確性。若之後要把這份 DIY 補齊，建議在 `record_request_sli` 的 `finally` 區塊裡，於呼叫 `call_next` 前後分別打點，並在 handler 呼叫 provider adapter 前後再打點一次，即可還原三段式的時間拆分，不需要更動既有的 taxonomy 或 middleware 註冊順序。

## 延伸思考

Day 17 的核心是「夠好的 SLI 不需要追求完美」：

1. **三層區分**：technical availability (HTTP 層) vs. quality (semantic 層) vs. dependency health (下游層)
2. **低基數設計**：label 數量穩定，避免時間序列爆炸
3. **Fixture 驅動**：先列舉真實反例，再定義 SLI；而不是倒過來
4. **Handler 負責**：只有業務邏輯層知道「這個錯誤代表什麼」，middleware 只負責量

下一步（Day 18）會在 LLM workflow 中擴展這套框架，處理 TTFT、token throughput、retrieval failure 等 AI 特有的信號。但基礎概念已在這裡奠定：分子與分母清楚，反例明確，就能支撐值班決策。

## .env 設定

`.env.example` 中沒有敏感資訊（此 DIY 純 mock，不呼叫真實 API）。
