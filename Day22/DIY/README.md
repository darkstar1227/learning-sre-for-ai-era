# Day22 DIY — Three-Layer Dashboard Design + Observability Implementation

對應 [Day22/Day22.md](../Day22.md) 的實作驗證。獨立 `uv` 專案，包含：
1. **設計驗證**（第⑪節）：用 Pydantic 模型驗證三層框架的邏輯正確性
2. **工作程式碼實作**（第⑥節）：FastAPI `/ask` 端點 + Prometheus 指標，可實際執行與觀測

## 內容

```text
Day22/DIY/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI /ask endpoint + Prometheus metrics (section ⑥)
│   ├── metrics.py        # Prometheus Counter, Histogram, Gauge definitions
│   └── dashboard.py      # Three-layer dashboard data model + validators (section ⑪)
├── scripts/
│   └── generate_dashboard.py  # Generate and validate dashboard design
├── .env.example
├── Makefile
├── pyproject.toml
└── uv.lock
```

**核心概念**：Day22 文章強調「框架幫你漏斗化資訊，不是要把所有圖表塞進一頁」。本 DIY 專案驗證並實作：

- **User Layer**: Golden Signals 看企業成果（Good Outcome Ratio、Latency SLO、Error Budget Burn）
- **Service Layer**: RED 方法分離服務問題（Rate、Errors、Duration for `/ask`、retrieval、tool）
  - AI 特有訊號：Queue Delay、TTFT、Tool Failure、Evaluation Outcome
- **Resource Layer**: USE 方法診斷基礎設施瓶頸（Utilization、Saturation、Errors for worker、GPU queue、DB pool、DB、Redis）

每層都回答「一個清晰的問題」，而不是混雜。

**包含兩個部分**：
1. **Section ⑪ DIY Task**：三層框架設計驗證（Pydantic 模型 + 邏輯檢查）
2. **Section ⑥ Code Examples**：可運行的 FastAPI 實作 + Prometheus 指標export

## 執行方式

### 初始化環境

```bash
cd Day22/DIY
make sync            # 或 uv sync
```

### 驗證三層框架設計（Section ⑪）

```bash
make generate        # 或 uv run python scripts/generate_dashboard.py
```

成功執行會輸出：
- ✓ 驗證每一層使用正確框架（RED vs USE）
- ✓ AI 特有訊號（Queue Delay、TTFT、Tool Failure、Evaluation）檢查
- ✓ 完整的三層 dashboard 結構摘要

### 啟動 FastAPI 伺服器（Section ⑥）

**終端 1：啟動伺服器**
```bash
make server          # 或 uv run python -m app.main
# Uvicorn running on http://0.0.0.0:8000
```

**終端 2：測試端點**
```bash
make test-endpoint   # 執行測試請求並檢視 /metrics
```

或手動測試：
```bash
# 測試 /ask 端點
curl -X POST "http://localhost:8000/ask?question=What+is+SRE"

# 檢視 Prometheus 指標
curl "http://localhost:8000/metrics/" | grep ai_
```

### 清理

```bash
make clean
```

## 實測結果

### 設計驗證（make generate）

成功執行，驗證輸出：
```
Validating dashboard design...
✓ All three layers (User, Service, Resource) are present
✓ User layer uses correct method (RED ≠ USE)
✓ Service layer uses correct method (RED ≠ USE)
✓ Resource layer uses correct method (RED ≠ USE)
✓ AI-specific signals (queue delay, TTFT, tool failure, evaluation) are present

All validations passed!
```

### FastAPI 伺服器與指標（make server + test-endpoint）

成功執行，驗證項目：

- [x] FastAPI `/ask` 端點可正常執行
  - ✓ Server starts on http://0.0.0.0:8000
  - ✓ POST /ask?question=... returns {"answer": "...", "outcome": "ok"}
  - ✓ GET /health returns {"status": "ok"}

- [x] Prometheus 指標正確 export（Day22 section ⑥ 第 2 點）
  - ✓ `/metrics/` endpoint 返回 Prometheus 格式指標
  - ✓ ai_requests_total (Counter) 有低基數 labels: route, outcome, model_route
  - ✓ ai_request_duration_seconds (Histogram) 有 _bucket, _count, _sum
  - ✓ ai_ttft_seconds (Histogram) 記錄 TTFT
  - ✓ ai_queue_wait_seconds (Histogram) 記錄 queue wait
  - ✓ ai_queue_depth (Gauge) 追蹤當前隊列長度
  - ✓ ai_workflow_steps_total (Counter) 記錄各步驟結果

- [x] 指標量測點位置正確（Day22 section ⑥ 第 3 點）
  - ✓ QUEUE_DEPTH: request 進入前 inc(), 完成後 dec()
  - ✓ QUEUE_WAIT: 量測 worker acquired 時間點
  - ✓ TTFT: 在 workflow 完成後立即 observe（模擬首個 token 出現）
  - ✓ REQUEST_DURATION: 在 finally 區塊，確保無論成功或失敗都被記錄

- [x] 每層有明確讀者與問題（設計驗證）
  - User Layer: 讀者 = Product Managers / On-call / Customer Success；問題 = 用戶是否滿意 + SLO 達成 + Error budget 燒速
  - Service Layer: 讀者 = Backend engineer / On-call / Platform team；問題 = 哪個服務/元件在失敗或變慢
  - Resource Layer: 讀者 = Infrastructure engineer / On-call SRE；問題 = 基礎設施能否應對負載

### 實際跑起來之後，跟文章描述對得上的地方

跑 `make server` 之後，第一件會注意到的事是：`ai_queue_depth` 這個 Gauge 在完全沒有流量進來時就已經 export，值是 `0.0`，而不是像某些實作那樣「第一筆請求進來才第一次出現這個指標」。這件事看起來瑣碎，但正好對應文章第 ⑥ 節強調的「Gauge 從一開始就要有初始值，不能等第一次 `.inc()` 才讓它出現」——如果 Gauge 只在被呼叫過一次之後才出現在 `/metrics/` 輸出裡，Prometheus 在服務剛啟動、還沒有任何請求時去 scrape，會拿到「這個指標不存在」而不是「這個指標是 0」，兩者在 PromQL 裡的行為不一樣：前者會讓 `sum(ai_queue_depth)` 因為 no-data 而不畫線，後者才會正確畫出一條貼著 0 的線。

連續打十次 `curl -X POST "http://localhost:8000/ask?question=..."`，然後看 `ai_request_duration_seconds_bucket` 的輸出，會發現預設的 bucket 邊界（0.1, 0.25, 0.5, 1, 2.5, 5, 10 秒）對這個模擬端點來說幾乎沒有鑑別力——因為 `main.py` 裡用 `asyncio.sleep(random.uniform(0.05, 0.3))` 模擬處理時間，所有請求全部落在 `le="0.5"` 這個 bucket 裡，看不出分佈的形狀。這其實是文章第 ⑤ 節「bucket 邊界要對齊你關心的 SLO 閾值，而不是抄預設值」的一個活生生示範：如果拿這組 bucket 去量測一個 P95 目標是 3 秒的服務，同樣會遇到「資料進得去，但每個 bucket 都是空的或都是滿的」問題，圖表看起來有資料，但完全沒有鑑別力可言。

### 跟文章描述不完全一致、需要留意的地方

`ai_ttft_seconds` 這個 Histogram 目前是在 `await call_workflow(...)` **完成之後**才 `observe()`，也就是說目前的實作其實記錄的是「端到端處理時間的某個近似值」，而不是文章第 ⑥ 節精確定義的「從請求進入到第一個 token 真正送到使用者手上的時間」。這是因為這個 DIY 端點沒有做真正的 SSE streaming（`StreamingResponse` + `yield`），只是一次性回傳完整字串。這個落差被記錄在下面「發現的問題與修正」第 7 點，讀者如果要精確驗證文章談的 TTFT 語意，需要自行把 `/ask` 改成 streaming 端點，在第一個 `yield` 的當下打 timestamp。

- [x] RED 與 USE 沒有套錯對象（設計驗證）
  - User & Service layers 用 RED（request-based）
  - Resource layer 用 USE（capacity-based）
  - 驗證邏輯在 `app/dashboard.py` 的 `DashboardLayer.validate_no_method_confusion()` 正確拒絕混淆

- [x] AI 特有訊號能回到 user outcome（設計驗證）
  - Service layer 包含：Queue Delay、TTFT、Tool Failure、Evaluation Outcome
  - 這些都明確說明「一旦紅色要做什麼」
  - 所有 Service 層 alert 都點到 Resource 層排查

### 驗證詳細項目

執行 `make generate` 的輸出日誌：

```
Validating dashboard design...

✓ All three layers (User, Service, Resource) are present
✓ User layer uses correct method (RED ≠ USE)
✓ Service layer uses correct method (RED ≠ USE)
✓ Resource layer uses correct method (RED ≠ USE)
✓ AI-specific signals (queue delay, TTFT, tool failure, evaluation) are present

All validations passed!
```

Pydantic 模型檢驗：
- `DashboardChart`: 每個圖表都有 name、metric_type、question、red_flag_action
- `DashboardLayer`: 每層都有 name、purpose、readers、charts，並驗證 RED/USE 不混淆
- `ThreeLayerDashboard`: 驗證三層全到位、AI 訊號回到 outcome

## 發現的問題與修正

1. **Day22 文章既有設計驗證（section ⑪），也有工作程式碼（section ⑥）。**
   - 初版 DIY 只實作了 section ⑪（三層框架驗證）
   - **修正**：補加 section ⑥ 的 FastAPI 實作（app/main.py + app/metrics.py）
   - 現在 DIY 包含：Pydantic 驗證 + 可執行的 FastAPI 伺服器 + 真實 Prometheus 指標export
   - **好處**：不只驗證框架邏輯，還能看到指標實際 export 的樣子

2. **AI 訊號該放在哪一層？**
   - 文章提到「AI workflow 要額外放入 queue delay、TTFT、tool failure、evaluation outcome」，但沒有明確說位置
   - **設計決定**：放在 Service layer（RED）而非 User 或 Resource
     - 理由：這些都是請求級別（request-scoped）的屬性，符合 RED 而非 USE
     - Queue delay 和 TTFT：「某個特定 LLM 請求花多久」→ Duration 維度
     - Tool failure 和 Evaluation outcome：「某個 tool/evaluator 對這個請求如何」→ Errors 維度
   - 驗證邏輯自動檢查這些訊號是否存在

3. **Prometheus /metrics 端點重定向問題**
   - `make_asgi_app()` mount 到 `/metrics` 後，curl 取得 307 重定向
   - **原因**：Prometheus ASGI app 期望路徑末尾有 `/`
   - **影響**：`curl "http://localhost:8000/metrics/"` (加尾鑄) 或 `curl -L` (跟隨重定向) 都能工作
   - **已驗證**：指標確實 export，只是路由需多一個 `/`

4. **標籤基數控制**
   - Day22 section ⑥ 強調不要在 label 放 request_id、user_id、prompt 等高基數值
   - 本實作遵守：ai_requests_total 只用 `route`、`outcome`、`model_route` 三個低基數 label
   - outcome 被刻意限制在可預測的集合（ok、technical_error、upstream_timeout 等）

5. **Section ⑥ 情境 A 與 B 的驗證**
   - 文章要求驗收清單的「情境 A（上游逾時）與 B（worker 並行度低）」
   - 本 DIY 尚未實作模擬這兩個情境的程式碼（只有基本 stub）
   - **原因**：DIY 專注於框架驗證 + 指標export，情境測試可由使用者在此基礎上擴展
   - **後續步驟**：可在 app/main.py 加入環境變數開關（e.g., `CHAOS_ENABLED`) 來注入延遲或錯誤

6. **所有依賴正確 resolve**
   - FastAPI、uvicorn[standard]、prometheus-client 在 Python 3.14 上都可用
   - uv.lock 已生成（21 packages）

7. **`ai_ttft_seconds` 目前量測的其實不是嚴格定義的 TTFT**
   - Day22 文章第 ⑥ 節把 TTFT 定義為「使用者感知到第一個 token 出現」的時間，這個定義只有在真正的 streaming 回應（SSE 或 chunked transfer）下才有意義
   - 目前 `/ask` 端點是一次性回傳完整 JSON（`{"answer": "...", "outcome": "ok"}`），`observe()` 是在整個 `call_workflow()` 完成後才呼叫
   - **後果**：`ai_ttft_seconds` 目前實質上等於整個請求的處理時間，跟 `ai_request_duration_seconds` 高度重疊，沒有反映出文章強調的「TTFT 和端到端時間是兩個獨立指標，一個可能很短、一個可能很長」
   - **修正方向（未落地，留給讀者延伸）**：把 `/ask` 改成 `StreamingResponse`，在 `call_workflow()` 內部第一個 `yield` 的當下記錄時間戳、與請求開始時間相減，才是文章定義的 TTFT
   - 這個落差本身也是一個教訓：光是 metric 名稱叫 `ttft`，不代表量測邏輯真的符合 TTFT 的語意——第 ⑧ 節「圖有資料不等於量測正確」講的正是這一類問題，DIY 專案自己就踩到了一個實例

8. **`ai_queue_depth` 在單 worker、低併發下很難觀察到非零值**
   - 用 `make test-endpoint` 這種序列化的單一請求測試，`ai_queue_depth` 幾乎不會離開 0，因為請求進來、`inc()`、處理、`dec()` 全部在毫秒等級內完成，下一個請求進來時前一個早就結束了
   - 要實際看到 queue depth 堆高，需要用 `hey` 或 `wrk` 之類的工具同時打出遠高於 worker 併發上限的請求量（例如同時 50 個併發打進一個只設定 `asyncio.Semaphore(2)` 的端點），這點文章第 ⑦ 節的情境 B 已經點出但 DIY 程式碼本身沒有內建這樣的負載產生器
   - **後續步驟**：可以在 `scripts/` 底下加一支用 `httpx.AsyncClient` 搭配 `asyncio.gather()` 同時發送大量併發請求的小工具，才能真正把 queue depth 的曲線畫出形狀，而不是永遠貼著 0

---

**小結**：本 DIY 包含設計驗證（三層框架邏輯）+ 工作程式碼實作（FastAPI /ask + Prometheus 指標）。每層都回答清晰的問題、不混淆方法、AI 訊號能回到用戶 outcome。指標可實際 export 到 /metrics，可與 Prometheus scraper 或 Grafana 整合。實測過程中也發現了兩個「指標存在，但語意跟文章定義有落差」的實例（TTFT、queue depth 在低併發下的可觀察性），這些落差本身恰好印證了文章反覆強調的一件事：**有指標名稱、有數字輸出，不等於量測的東西真的是你以為的那個東西**。
