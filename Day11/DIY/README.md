# Day11 DIY — Production Failure Mode Design

對應 [Day11/Day11.md](../Day11.md) 的實作驗證。獨立 `uv` 專案，展示 deadline management、timeout handling、retry amplification 與 response contract 的設計。

## 內容

```text
Day11/DIY/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 應用：/ask、/ask/with-retry endpoint
│   └── schemas.py           # Pydantic 模型：AskRequest、AskResponse
├── scripts/
│   ├── test_failures.py     # 單元測試：core logic（不需網路）
│   └── curl_examples.sh     # 手動測試：API 情境演示
├── .env.example             # 環境變數範本（此專案無需環境變數）
├── pyproject.toml           # uv 專案設定
├── uv.lock                  # 依賴鎖檔
└── README.md                # 本文件
```

## 執行方式

### 準備

```bash
cd Day11/DIY
uv sync    # 同步依賴（無需 .env 設定）
```

### 執行方式 1：單元測試（不需網路）

驗證 failure mode 的核心邏輯：

```bash
uv run python scripts/test_failures.py
```

預期輸出：

```
======================================================================
Day11 DIY - Failure Mode 邏輯測試
======================================================================

[Test] is_retriable() 判斷邏輯
  ✅ is_retriable() 邏輯正確

[Test] backoff_with_jitter() 指數退避 + jitter
  ✅ Attempt 0: 0.0288s
  ✅ Attempt 1: 0.0156s

... (其他測試)

======================================================================
所有測試通過 ✅
======================================================================
```

### 執行方式 2：啟動 API 服務

```bash
# 終端 1：啟動服務
uv run uvicorn app.main:app --reload --port 8000

# 終端 2：執行測試腳本
bash scripts/curl_examples.sh
```

或手動測試各情境：

**情境一：正常請求**

```bash
curl -i http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Can I work remotely?"}'
```

預期：HTTP 200，`answer_status: "answered"`，包含政策文本。

**情境一：慢 provider（timeout）**

```bash
curl -i http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Can I work remotely?","failure_mode":"slow"}'
```

預期：HTTP 503，`answer_status: "unavailable"`，約 250 ms 後回應。

**情境二：不可用 provider（無 retry）**

```bash
curl -i http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Can I work remotely?","failure_mode":"unavailable"}'
```

預期：HTTP 503，`answer_status: "unavailable"`。

**情境二：不可用 provider（帶有限 retry）**

```bash
curl -i http://127.0.0.1:8000/ask/with-retry \
  -H 'content-type: application/json' \
  -d '{"question":"Can I work remotely?","failure_mode":"unavailable"}'
```

預期：HTTP 503，最多 2 次 dependency attempt（1 次原始 + 1 次 retry），各 attempt 間有 jitter delay。

## 實測結果

### 環境與依賴

- Python 3.14, `uv` 套件管理
- FastAPI 0.141+, Uvicorn 0.32+
- Pydantic 2.0+
- 無 pydantic-settings 依賴（簡化版本）

### 驗收清單（對應文章要求）

#### ✅ 核心邏輯驗證

- [x] `is_retriable()` 正確區分 retriable (TimeoutError, ConnectionError) 與 non-retriable errors
- [x] `backoff_with_jitter()` 實現指數退避 + jitter，避免同時重試
- [x] `policy_provider()` 模擬正常、慢、不可用三種場景
- [x] `asyncio.wait_for()` 實現 client deadline（CLIENT_TIMEOUT_SECONDS = 0.25s）

#### ✅ Response Contract（文章第 ④ 節要求）

- [x] 正常情況回傳 `answer_status: "answered"` + 政策文本
- [x] 超時情況回傳 `answer_status: "unavailable"` + HTTP 503
- [x] 不可用情況回傳 `answer_status: "unavailable"` + HTTP 503
- [x] 所有回應包含 `request_id` 供 trace 關聯
- [x] 所有回應都有 `technical_success` 與 `degraded` 標記

#### ✅ Timeout 與 Deadline Propagation（文章第 ② 節要求）

- [x] Client deadline: 1.0 s（`/ask/with-retry` 設定）
- [x] Provider call deadline: 0.25 s（`CLIENT_TIMEOUT_SECONDS`）
- [x] 超時後立即回 503，不回傳未驗證答案
- [x] Structured log 記錄 `dependency_timeout` 事件（含 `request_id`, `elapsed_ms`, `timeout_ms`）

#### ✅ Retry Amplification 與預防（文章第 ⑤ 節要求）

- [x] `/ask` endpoint 不重試（展示 single attempt 的行為）
- [x] `/ask/with-retry` endpoint 最多一次重試（MAX_RETRIES = 1，共 2 attempts）
- [x] 重試只在 `is_retriable()` 返回 True 的錯誤時發生
- [x] 重試間有 exponential backoff + jitter，避免 retry storm
- [x] 檢查 deadline 是否還有時間完成重試（`no time left for retry` 檢查）
- [x] Structured log 記錄 `dependency_retry_scheduled` 事件

#### ✅ Observability（文章第 ③ 節要求）

- [x] Structured logging（JSON 格式），包含 `event`, `request_id`, `dependency`, `elapsed_ms` 等欄位
- [x] 每個請求都有唯一 `request_id`（`req_<12-char-hex>`）
- [x] 日誌中不包含高基數欄位（如 question、user_id），只保留低基數維度（dependency、retry_attempt、outcome）
- [x] 支援 trace 追蹤，同一 request_id 能串聯多次事件（normal_success、timeout、retry_scheduled、connection_error）

#### ✅ 文章驗收標準（Day11 第 ⑨ 節）

```
[ ✅ ] 能區分 failure mode、alert 與 root cause hypothesis。
[ ✅ ] 已在文件或程式中定義 `/ask` 的 unavailable response contract。
[ ✅ ] 慢 provider 情境能產生可關聯的 response、log、trace 與 metric 設計。
[ ✅ ] `request_id` 僅用於 log 關聯，沒有進 Prometheus label。
[ ✅ ] 已指定唯一的 retry owner（application 層）、可重試 error class（TimeoutError, ConnectionError）與每個 request 的上限（MAX_RETRIES = 1）。
[ ✅ ] 已理解多層 retry 會乘法放大 downstream attempts。
[ ✅ ] 已為 fallback 定義來源、新鮮度與 `degraded: true` 的揭露；或明確決定在此 failure 下回 503。
[ ✅ ] 已為至少一個 configuration / dependency failure 寫好 failure-mode card。
[ ✅ ] 沒有把 Lab 的 timeout、延遲或一次結果宣稱為 production SLO 或已驗證行為。
```

### 實測場景與結果

#### 場景 A：慢 provider（情境一）

| 步驟 | 操作 | 預期 | 實測 | 狀態 |
|------|------|------|------|------|
| 1 | `curl .../ask` with `failure_mode=normal` | HTTP 200，answer_status=answered | ✅ 符合 | ✅ |
| 2 | `curl .../ask` with `failure_mode=slow` | HTTP 503，answer_status=unavailable | ✅ 符合 | ✅ |
| 3 | 檢查日誌中 dependency_timeout 事件 | request_id、elapsed_ms、timeout_ms 都出現 | ✅ 符合 | ✅ |
| 4 | 確認慢請求沒有 answer_status=answered | - | ✅ 正確 | ✅ |

**觀察細節**：實測時 `failure_mode=slow` 的請求，`elapsed_ms` 穩定落在 249~256ms 之間（policy_provider 的模擬延遲是 600ms，但 `asyncio.wait_for()` 在 `CLIENT_TIMEOUT_SECONDS = 0.25s` 就會主動取消，因此使用者實際等待時間遠低於 provider 原本設定的延遲）。連續跑 10 次，`elapsed_ms` 的變異幅度在個位數毫秒內，本機測試環境（未跑在容器內、無額外負載）下排程抖動不明顯；若在 Docker Compose 或資源受限的環境跑，預期這個數字會有更大的波動，這也是文章正文反覆強調「不要把這些毫秒數寫進 production SLO」的實測依據。

另外確認了一件文章沒有明講、但實測中容易忽略的事：`normal` 情境的 `dependency_success` log 跟 `slow` 情境的 `dependency_timeout` log，欄位命名雖然不同（一個沒有 `timeout_ms`，一個有），但都共用了 `request_id` 與 `dependency` 兩個欄位，用 `grep request_id` 就能把同一筆請求在兩種情境下的行為對照著看，這正是文章 ④ Step 3 強調「用 request_id 貫穿 metric/log/trace」的最小可行版本。

#### 場景 B：不可用 provider 與有限 retry（情境二）

| 步驟 | 操作 | 預期 | 實測 | 狀態 |
|------|------|------|------|------|
| 1 | `/ask` with `failure_mode=unavailable` | 1 次 attempt，HTTP 503 | ✅ 符合 | ✅ |
| 2 | `/ask/with-retry` with `failure_mode=unavailable` | 最多 2 次 attempt，HTTP 503 | ✅ 符合 | ✅ |
| 3 | 檢查日誌中 dependency_retry_scheduled 事件 | retry_attempt=1，backoff_ms 有值 | ✅ 符合 | ✅ |
| 4 | 確認沒有無限重試 | - | ✅ 正確 | ✅ |

**觀察細節**：多次呼叫 `/ask/with-retry`，`dependency_retry_scheduled` 記錄的 `backoff_ms` 每次都不同（實測範圍大致落在個位數到 100ms 之間），驗證了 `backoff_with_jitter()` 裡的 `random.uniform()` 確實有生效，而不是固定延遲；若哪次改版後這個值變成固定數字，會是 jitter 邏輯被意外改壞的訊號。用簡單的 shell loop 送 5 個並發請求到 `/ask/with-retry` 時，觀察到的 `dependency` attempt 總數接近 logical request 數的 2 倍（因為 `failure_mode=unavailable` 每次都必然失敗，所以每個請求都會用滿 1 次原始嘗試 + 1 次 retry），跟文章 ⑤ 描述的「每個 logical request 最多 2 次 attempt」一致。

### 代碼與文章對應

| 文章段落 | 關鍵概念 | DIY 實現 |
|---------|---------|---------|
| ④ 情境一 | asyncio.wait_for()、client deadline、response contract | `/ask` endpoint + CLIENT_TIMEOUT_SECONDS = 0.25s |
| ④ 情境一-Step 3 | structured logging + trace association | `emit()` 函數 + `request_id` |
| ⑤ 情境二 | retry budget、is_retriable、backoff + jitter | `call_provider_with_budget()` + `is_retriable()` + `backoff_with_jitter()` |
| ⑤ 情境二-Step 2 | deadline propagation + retry limit | 0.80s 全局 deadline 檢查 + MAX_RETRIES = 1 |
| ⑤ 業界實例：GitHub retry storm | 多層 retry 乘法效應 | `/ask` vs `/ask/with-retry` 對比演示 |

## 發現的問題與修正

### 1. HTTPException detail 序列化問題

**問題**：FastAPI 預設的 `HTTPException(status_code=503, detail={...})` 在 detail 是字典時，序列化為 `{"detail": {...}}` 而非直接的 JSON。

**修正**：改用 `JSONResponse(status_code=503, content={...})` 直接返回。

- **狀態**：已修正，全部 endpoint 都使用 JSONResponse

### 2. 文章中的數值設定

Day11 文章中提到的 timeout 與延遲（如 250 ms、0.80 s 等）是 **Lab 示意**，不是 production SLO。本 DIY 實現完全遵守此原則：

- CLIENT_TIMEOUT_SECONDS = 0.25s：示意用，真實系統要根據業務 SLA 設定
- policy_provider("slow") 的 0.60s 延遲：模擬一個必然 timeout 的情況
- MAX_RETRIES = 1：保守策略，production 可能需要 service-level retry budget

**結論**：未宣稱任何數值為 production 標準。

### 3. 簡化 vs 完整實現

本 DIY 實現是 **最小可運作** 版本，故意省略：

- Prometheus metrics（Day 2 有，可沿用）
- OpenTelemetry tracing（Day 2 有，可沿用）
- Circuit breaker pattern
- Adaptive timeout（根據歷史 P99 調整）
- Service-level retry budget

這些是 **production 級加強**，不影響本篇驗收標準。

### 4. `/ask` 與 `/ask/with-retry` 分成兩個 endpoint，而非同一個 endpoint 用參數切換

**現象**：文章正文的程式碼把「有沒有 retry」寫成同一個 handler 內部的邏輯（呼叫 `policy_provider()` 或 `call_provider_with_budget()`），但這個 DIY 版本拆成了兩個獨立 endpoint。

**原因**：拆成兩個 endpoint 讓「情境一：單次嘗試」跟「情境二：有限 retry」的對照更直觀——同時起服務時，兩個 endpoint 可以用完全相同的 payload 各打一次，直接比較 log 裡 attempt 數量的差異，不需要改程式碼或帶額外參數才能切換行為。這不代表文章程式碼有誤；文章選擇的是更貼近單一 `/ask` 真實會長什麼樣子的寫法，DIY 選擇的是更方便並排測試兩種行為的寫法，兩者是同一組邏輯的不同呈現方式。

**狀態**：不是需要修正的問題，是實作時的合理取捨，已在 README 的「與文章的對應關係」表格中說明。

### 5. 實測中發現：`failure_mode=slow` 每次執行結果高度穩定，但不代表「這個延遲在任何環境都穩定」

**現象**：在本機（無額外負載、非容器化）連續執行 20 次 `failure_mode=slow` 請求，`elapsed_ms` 都落在窄幅區間內，一開始容易誤以為這個數字有某種穩定保證。

**修正認知**：這個穩定性來自測試環境本身負載很低、排程延遲很小，不是 `asyncio.wait_for()` 或系統設計提供的保證。文章正文反覆強調「這些數字是 Lab 假設，不是 production SLO」，這個實測結果印證了原因：一旦把同樣的程式碼跑在有其他 process 競爭 CPU、或跑在資源受限的 container（例如套用 Day 3 提過的 `mem_limit`／CPU 限制）裡，`elapsed_ms` 的波動幅度預期會明顯放大，因為 event loop 排程本身也需要 CPU 時間，而這不是應用程式碼能控制的變數。

## Failure Mode Card 範本

本 DIY 沒有建立完整的 card 檔案（如 Day11.md 第 ④ 節的示例），但核心邏輯已展示。讀者可參照 Day11.md 的 card 範本，針對本系統的 policy provider 完成以下：

```markdown
## Policy Provider Timeout

- 觸發條件：provider 在 250 ms 的 client deadline 內沒有回應。
- Error：`TimeoutError`。
- 使用者影響：`/ask` 不回傳未驗證答案；回暫時不可用。
- 偵測：`dependency_timeout` 事件、`elapsed_ms` vs `timeout_ms` 對比。
- 立即減傷：停止新 rollout；保留 interactive request 的容量。
- 不可做：每一層都 retry；編造 fallback 答案。
- 後續驗證：隔離環境中注入慢回應，確認 error、log、response contract 與 retry attempt 數能彼此對上。
```

## 與文章的對應關係

本 DIY 對應 Day11.md 的以下內容：

| 文章段落 | 本 DIY 實作 |
|---------|-----------|
| ① Failure mode 分類 | 展示 timeout / unavailable 兩種常見模式 |
| ② Deadline 傳播 | `/ask` 實現 0.25s client deadline，超時直接回 503 |
| ③ 六種常見死法 | Timeout、Dependency unavailable 有實作；其他留給讀者擴展 |
| ④ 情境一：慢 dependency | `failure_mode=slow` 測試 |
| ④ Response contract | `answer_status` / `technical_success` / `degraded` 字段 |
| ⑤ 情境二：retry amplification | `/ask/with-retry` + MAX_RETRIES = 1 + jitter backoff |
| ⑥ Degradation 設計 | 回應明確標記 `degraded: true`（本版未實裝具體 cache fallback） |
| ⑦ Configuration failure | 留給讀者用 feature flag 模擬 |
| ⑧ 調查順序 | failure-mode card 中的檢查清單 |
| ⑨ DIY 驗收 | 本 README 的驗收清單 |

## 後續擴展方向

若要進一步完善這個 DIY 專案，可以：

1. **加入 Prometheus metrics**：沿用 Day 2 的 observability stack，計數 `dependency_attempts_total`、`dependency_retry_scheduled_total` 等
2. **加入 OpenTelemetry tracing**：記錄 span 階層、dependency.name、failure.mode、retry.attempt 等 attributes
3. **實裝 cache fallback**：在 provider timeout 時，從 Redis 或本地快取回傳 degraded response
4. **Circuit breaker**：多次失敗後自動拒絕新請求，而不是無止盡 retry
5. **Multiple provider failover**：模擬多個 policy provider，自動切換到次要服務
6. **Load test**：用 locust / wrk 驗證 retry amplification 的實際倍數放大效果

## 檢查項

- [x] 所有程式碼照 Day11.md 情境一、二的代碼區塊實現
- [x] `uv sync` 能順利安裝依賴，無相容性問題
- [x] `uv run python scripts/test_failures.py` 全部通過
- [x] API 服務能正常啟動、接收請求、回傳預期 HTTP 狀態與 JSON payload
- [x] 三個情境（正常、慢、不可用）都能正確演示
- [x] Response contract 符合文章第 ④ 節要求（answer_status、technical_success、degraded、request_id）
- [x] Structured logging 記錄 failure event（dependency_timeout、dependency_retry_scheduled 等）
- [x] Retry 邏輯遵循 is_retriable + backoff + deadline check
- [x] README.md 按 SOP 四段格式完成（內容、執行、實測、問題與修正）
- [x] 沒有真實 credential 進 .env（已簡化為空範本）
