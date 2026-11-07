# Dashboard Design: Learning SRE for the AI Era

> 對應 [Day24/Day24.md](../Day24.md) 的文字設計驗證  
> 情景：監控 AI RAG 系統（FastAPI + Gemini + LangSmith + Loki/Prometheus/Tempo）  
> 故障情景：`upstream_timeout` - Gemini API 回應超時  
> 架構：六層遞進式設計（User Experience → Service Overview → API → Dependencies → Infrastructure → AI/GPU）

---

## 層級一：User Experience（首頁 - 午夜 3 點必看）

**讀者：** on-call 值班工程師  
**決策：** 有無使用者影響，是否需要立刻處理  
**時間窗：** 28 天（SLO）+ 5 分鐘（短窗 burn rate）

### Panel 1: Good Outcome SLI (Goal-based)
```
Title:        "Good Outcome Rate (28d SLO)"
Owner:        @oncall-ai-platform
Metric:       SLI = (successful_outcomes / total_requests)
Threshold:    99.5% (28-day SLO)
Short Window: 5min burn rate [current: 95.2%] ⚠️ degraded
Alert Rule:   if SLI < 99.0% for 2 min → page
Drill-down:   → "View Service Overview"
              [link] → /dashboards/service-overview
Status Now:   ✓ HEALTHY (99.7%)
```

**問題定義：** 使用者感知「系統有沒有如預期完成 RAG 查詢並產生答案」  
**特點：** 第一層只看 outcome，不看成因；成因層指標放在下面層級

---

### Panel 2: API Latency P95 (SLO)
```
Title:        "API Latency P95 (SLO)"
Owner:        @oncall-api
Metric:       histogram_quantile(0.95, http_request_duration_seconds) [/api/ask]
Threshold:    ≤ 2.5s (99%)  ← SLO line (solid)
Warning:      ≤ 2.0s (95%)  ← burn rate line (dashed)
Drill-down:   → "View Service Overview"
              [link] → /dashboards/service-overview
Current:      2.18s ⚠️ approaching SLO
```

**問題定義：** 使用者感知「請求要多久才能得到答案」  
**特點：** P95 而非平均；接近 SLO 需要鑽下去

---

### Panel 3: Error Rate (5xx)
```
Title:        "Error Rate (5xx)"
Owner:        @oncall-api
Metric:       rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
Threshold:    ≤ 0.1% (SLO: 99.9%)
Drill-down:   → "View Service Overview"
              [link] → /dashboards/service-overview
Current:      0.08% ✓ OK
```

---

## 層級二：Service Overview（整體健康度 - 判斷是否需要升級 incident）

**讀者：** on-call、值班主管  
**決策：** 是否升級為 critical incident、是否通知 leadership  
**時間窗：** 5 分鐘（實時檢測）、對比前一小時（找趨勢）

### Panel 4: /ask 路由全貌（Golden Signals）
```
Title:        "/ask Service Health (Golden Signals)"
Owner:        @oncall-service-owner
Metrics:
  - Latency:   histogram_quantile(0.95, ask_duration_seconds)
  - Traffic:   rate(ask_requests_total[5m]) by (is_retry)
  - Errors:    rate(ask_requests_total{status="error"}[5m])
  - Saturation:(active_ask_requests / max_concurrent)
Threshold:    Latency ≤ 2.5s | Traffic normal ±20% | Errors < 0.5% | Saturation < 80%
Drill-down:   → "View API Breakdown"
              [link] → /dashboards/ask-api-red
Current:      Latency: 2.18s ⚠️ | Traffic: 45.2 req/s（new: 43.8 / retry: 1.4）✓ | Errors: 0.32% ✓ | Saturation: 52% ✓
```

Note: Traffic 拆出 `is_retry` 維度，避免重試風暴和真實流量成長被誤判成同一種暴增（參考 Cloudflare 2025-09-12 dashboard outage 的監控間隙教訓）。

**問題定義：** 整個 /ask 服務是否作為一個黑盒子正常運作  
**特點：** 只看聚合四大信號，不拆細節；故障時知道「是慢」「是爛」「是卡」中的哪一個

---

## 層級三：API（工程師責任層 - 找到慢的那一步）

**讀者：** 負責該服務的工程師  
**決策：** 是 prompt_build、retrieval、model 還是 tool 慢  
**時間窗：** 5 分鐘

### Panel 5: Prompt Build & Retrieval RED
```
Title:        "Prompt Build & Retrieval (Step RED)"
Owner:        @oncall-workflow
Metrics:
  - Prompt build rate:     rate(prompt_build_total[5m])
  - Prompt build latency:  histogram_quantile(0.95, prompt_build_duration_seconds)
  - Retrieval rate:        rate(retrieval_calls_total[5m])
  - Retrieval latency:     histogram_quantile(0.95, retrieval_duration_seconds)
  - Retrieval success:     (successful_retrievals / total_retrieval_calls)
Threshold:    Prompt ≤ 100ms | Retrieval ≤ 800ms | Success ≥ 95%
Drill-down:   → "View Trace Search: Prompt/Retrieval"
              [link] → /loki?query={span_name=~"prompt|retrieval"}
Current:      Prompt: 45ms ✓ | Retrieval: 180ms ✓ | Success: 96.2% ✓
```

**問題定義：** prompt 和 retrieval 這兩個初期步驟有無問題  
**特點：** 如果這兩步都快，慢就在後面；如果這兩步慢，根因在這層

---

### Panel 6: Model Chat & Tool Execution RED
```
Title:        "Model Chat & Tool Execution (Step RED)"
Owner:        @oncall-workflow
Metrics:
  - Model call rate:       rate(model_calls_total[5m])
  - Model call latency:    histogram_quantile(0.95, model_call_duration_seconds)
  - Tool call success:     (successful_tool_calls / total_tool_calls)
  - Tool call latency:     histogram_quantile(0.95, tool_call_duration_seconds)
  - Fallback triggered:    rate(fallback_triggered_total[5m])
Threshold:    Model ≤ 2.0s | Tool ≤ 1.0s | Success ≥ 98% | Fallback < 2/min
Drill-down:   → "View Trace Search: Model/Tool"
              [link] → /loki?query={span_name=~"model|tool"}
              → "View LangSmith Session"
              [link] → langsmith.com/hub
Current:      Model: 1.85s ⚠️ | Tool: 250ms ✓ | Success: 97.8% ⚠️ | Fallback: 1.2/min ✓
```

**問題定義：** 核心推論流程（model chat）和 tool 使用有無故障  
**特點：** model 慢會直接拖累整體 latency；tool 失敗會影響 outcome

---

### Panel 7: Answer Validation & Response
```
Title:        "Answer Validation & Response Quality"
Owner:        @oncall-quality
Metrics:
  - Validation success:    (valid_answers / total_answers)
  - Response encoding lag: histogram_quantile(0.95, encoding_duration_seconds)
  - Quality score:         avg(quality_evaluation_score)
Threshold:    Validation ≥ 99% | Encoding ≤ 100ms | Quality ≥ 0.75
Drill-down:   → "View Quality Evaluator Traces"
              [link] → /loki?query={service="quality-eval"}
Current:      Validation: 99.3% ✓ | Encoding: 25ms ✓ | Quality: 0.82 ✓
```

**問題定義：** 最終答案是否符合品質標準  
**特點：** 不是 HTTP 200 就算成功；這層確認語義層的「good outcome」

---

## 層級四：Dependencies（外部依賴層 - 確認內外部問題）

**讀者：** 值班工程師  
**決策：** 依賴的 provider、DB 是否正常；是否能 failover  
**時間窗：** 5-10 分鐘

### Panel 8: LLM Provider Health (Gemini)
```
Title:        "Gemini API Provider Status"
Owner:        @oncall-platform
Metrics:
  - Request success rate:   (successful_requests / total_requests)
  - Request latency P95:    histogram_quantile(0.95, gemini_request_duration_seconds)
  - Timeout events:         rate(gemini_timeout_total[5m])
  - Rate limit errors:      rate(gemini_rate_limit_errors_total[5m])
  - Token usage rate:       rate(gemini_tokens_used_total[5m])
Threshold:    ≥ 99.5% success | ≤ 1.2s P95 | ≤ 5 timeouts/min
Drill-down:   → "View Gemini External Status Page"
              [link] → https://status.ai.google.dev
              → "View Gemini Client Logs"
              [link] → /loki?query={job="gemini-client"}
Current:      Success: 98.7% ⚠️ | P95: 1.92s ⚠️ | Timeouts: 8/min ⚠️
```

**問題定義：** 外部 LLM provider 是否可用  
**特點：** 影響 model.chat 步驟；超時 trigger fallback；無法控制但可監測、決策 failover

---

### Panel 9: Retrieval Service & Database
```
Title:        "Retrieval Service & Database Status"
Owner:        @oncall-retrieval-svc
Metrics:
  - Retrieval API availability: (successful_api_calls / total_api_calls)
  - Database conn pool:         (active_connections / max_connections)
  - Database query latency P95: histogram_quantile(0.95, db_query_duration_seconds)
  - Vector search latency:      histogram_quantile(0.95, vector_search_duration_seconds)
Threshold:    API ≥ 99% | Conn pool < 90% | Query ≤ 500ms | Vector search ≤ 600ms
Drill-down:   → "View Retrieval Service Logs"
              [link] → /loki?query={service="retrieval-api"}
              → "View PostgreSQL Metrics"
              [link] → /dashboards/postgres-connections
Current:      API: 99.8% ✓ | Conn pool: 28/50 ✓ | Query: 180ms ✓ | Vector: 170ms ✓
```

**問題定義：** 內部 retrieval 服務是否正常  
**特點：** 影響 retrieval 步驟；可控；需檢查池、連線、查詢

---

## 層級五：Infrastructure（基礎設施層 - 資源是否限制workflow）

**讀者：** 平台/SRE 團隊  
**決策：** 底層資源是否撐得住，是否需要擴容  
**時間窗：** 10 分鐘

### Panel 10: Compute Resources (CPU/Memory)
```
Title:        "API Service CPU & Memory Utilization"
Owner:        @oncall-infra
Metrics:
  - CPU utilization:      avg(rate(process_cpu_seconds_total[5m])) × 100
  - Memory usage:         process_resident_memory_bytes / available_memory
  - Memory pressure:      rate(out_of_memory_events_total[5m])
  - Thread pool size:     current_thread_pool_size / max_thread_pool
Threshold:    CPU < 80% | Memory < 85% | No OOM | Thread pool > 50%
Drill-down:   → "View Container Restart History"
              [link] → /dashboards/container-restarts
Current:      CPU: 42% ✓ | Memory: 62% ✓ | OOM: 0 ✓ | Thread pool: 180/256 ✓
```

**問題定義：** 計算資源是否耗盡  
**特點：** 不是根本原因，而是瓶頸指示器；高 CPU 可能代表邏輯問題，不能只看數字

---

### Panel 11: Network & Connection Pool
```
Title:        "Network I/O & Connection Pool Status"
Owner:        @oncall-infra
Metrics:
  - Network in/out:        rate(network_bytes_in_total[5m]), rate(network_bytes_out_total[5m])
  - Connection pool size:  (active_connections / max_pool_size)
  - Connection timeout:    rate(connection_timeout_total[5m])
  - Socket errors:         rate(socket_errors_total[5m])
Threshold:    In/Out < saturation | Pool < 90% | Timeouts < 1/min | Errors ≈ 0
Drill-down:   → "View Network Interface Stats"
              [link] → /dashboards/network-interfaces
Current:      In: 2.1 MB/s ✓ | Out: 1.8 MB/s ✓ | Pool: 45/100 ✓ | Timeout: 0 ✓
```

**問題定義：** 網路和連線是否限制吞吐  
**特點：** 影響所有 I/O 步驟；pool 耗盡會卡住 workflow；需要根據實際 bandwidth 調整門檻

---

## 層級六：AI / GPU（AI 特定資源層 - inference 隊列與加速器）

**讀者：** 平台/MLOps 團隊  
**決策：** GPU、推論佇列是否過載，是否需要降級或擴容  
**時間窗：** 5 分鐘

### Panel 12: GPU & Inference Queue
```
Title:        "GPU Utilization & Inference Queue Depth"
Owner:        @oncall-mlops
Metrics:
  - GPU utilization:       sum(nvidia_gpu_utilization) / count(gpus) × 100
  - GPU memory used:       sum(nvidia_gpu_memory_used_mb) / total_vram_mb × 100
  - GPU temperature:       max(nvidia_gpu_temperature_celsius)
  - Inference queue depth: length(pending_inference_queue)
  - Queue wait time P95:   histogram_quantile(0.95, queue_wait_duration_seconds)
Threshold:    GPU util < 85% | Memory < 90% | Temp < 80°C | Queue < 500 | Wait < 2.0s
Drill-down:   → "View GPU Scaling Events"
              [link] → /dashboards/gpu-autoscale-history
              → "View Model Batch Composition"
              [link] → /loki?query={job="batch-scheduler"}
Current:      GPU util: 62% ✓ | Memory: 51% ✓ | Temp: 54°C ✓ | Queue: 42 ✓ | Wait: 0.8s ✓
```

**問題定義：** GPU 加速器是否過載、inference 佇列是否堆積  
**特點：** AI 系統特有；直接影響 model.chat 的端到端延遲；autoscale 時的決策依據

**GPU util × Queue depth 判讀（GPU utilization 高不等於過載，需搭配 queue 一起看）：**

| GPU util | Queue depth | 判讀 | 處置 |
| :-- | :-- | :-- | :-- |
| 高 | 高 | 真的過載 | 擴容或降級 |
| 高 | 低 | 滿載但健康 | 不用動作 |
| 低 | 高 | 非 GPU 問題（batching/worker 異常） | 查 batch scheduler，不要盲目擴 GPU |
| 低 | 低 | 正常 | 不用動作 |

---

### Panel 13: Model Route & Batch Processing
```
Title:        "Model Route Distribution & Batch Efficiency"
Owner:        @oncall-mlops
Metrics:
  - Primary model rate:    rate(model_requests_total{route="primary"}[5m])
  - Fallback model rate:   rate(model_requests_total{route="fallback"}[5m])
  - Batch size avg:        avg(current_batch_size)
  - Batching efficiency:   (batched_tokens / total_tokens) × 100
  - Model switch events:   rate(model_route_change_total[5m])
Threshold:    Primary > 90% | Fallback < 10% | Batch size > 8 | Efficiency > 70%
Drill-down:   → "View Model Route Configuration"
              [link] → /dashboards/model-routing-config
              → "View Batch Scheduler Logs"
              [link] → /loki?query={service="batch-scheduler"}
Current:      Primary: 91% ✓ | Fallback: 9% ✓ | Batch: 16 ✓ | Efficiency: 78% ✓ | Switches: 0.3/min ✓
```

**問題定義：** 模型路由是否最優、batching 是否有效  
**特點：** Fallback 增加代表 primary 故障；低 batch efficiency 代表浪費 GPU；模型切換頻繁可能代表故障

---

## Request Trace Sample（逐筆診斷層 - 當聚合指標不夠時）

**鑽下來的入口：** 任何高 P95 或 error rate → trace search

### Panel 14: Single Trace Detail
```
Title:        "Sample Trace: /api/ask Request [request_id]"
Owner:        @oncall-sre
Data:         Single trace from Tempo/LangSmith, showing:
Timeline:
  0ms   |-- prompt_build (45ms)
  45ms  |-- retrieval (180ms)
        |   |-- vector_search (120ms)
        |   |-- rerank (60ms)
  225ms |-- model.chat (1850ms) ← **可能的瓶頸**
        |   |-- token generation
        |   |-- streaming output
  2075ms|-- answer_validate (20ms)
  2095ms|-- response_encoding (5ms)
  2100ms [TOTAL: 2100ms]

Drill-down:   → 若 model.chat 慢 → "View Panel 8 (Gemini)"
              [link] → /dashboards/gemini-provider
              → 若 queue wait 明顯 → "View Panel 12 (GPU Queue)"
              [link] → /dashboards/gpu-utilization
              → "View LangSmith Full Trace"
              [link] → langsmith.com/hub?session_id=[session]
Current:      Request ID: req_20260921_0345_abc123
              Workflow: policy_qa
              Model route: primary
              Quality result: pass
```

**問題定義：** 這一筆請求為什麼慢  
**特點：** 只看單一 request；包含 request_id 用於後續根因分析；span tree 指向上層 dependency 層

---

## 故障診斷路徑：`upstream_timeout` 情景

### 場景設定
午夜 3 點，on-call 收到 alert：「Good Outcome Rate 低於 99%」

### 首頁判斷（層級一 - 10 秒內判斷是否需要立刻行動）
```
1. 打開 dashboard 首頁
2. 看 Good Outcome SLI → ⚠️ 5min burn rate: 95.2%
3. 看 API Latency P95 → ⚠️ 2.18s (near SLO)
4. 看 Error Rate → ✓ 0.08% (OK)
   → 判斷：系統在「慢」而非「壞」，需要鑽下去找慢的根因

on-call 決策：「這不是全爆炸，但正在燒 SLO，進入診斷」
```

### 第二層診斷（層級二 - 確認故障在哪一層）
```
5. 點擊 Panel 1 或 2 的 Drill-down → 進到 Service Overview
6. 看 /ask Golden Signals
   - Latency ⚠️ 升高
   - Traffic ✓ 正常
   - Errors ✓ 低
   → 初步判斷：故障是 latency，不是容量或錯誤

on-call 決策：「問題是速度，需看具體步驟」
```

### 第三層詳查（層級三 - 找到慢的那一步）
```
7. 點擊 Service Overview 的 Drill-down → API Breakdown
8. 依序看各步驟：
   - Prompt build: 45ms ✓ OK
   - Retrieval: 180ms ✓ OK
   - Model chat: 1.85s ⚠️ **This is the problem!**
   - Tool: 250ms ✓ OK
   - Validation: 20ms ✓ OK
   → 明確根因：model.chat 慢

on-call 決策：「Model 是瓶頸，檢查 LLM provider」
```

### 第四層根因確認（層級四 - 確認內外部問題）
```
9. 點擊 Model Chat RED 的 Drill-down → Trace Search
10. 看幾條 slow trace，確認都是在 model.chat span
11. 點擊 trace 中的 drill-down → Gemini Provider Health
12. 看 Gemini metrics：
    - Success rate: 98.7% ⚠️（略微下降）
    - P95: 1.92s ⚠️（高於我們的預期）
    - Timeouts: 8/min ⚠️（比平時 ~1/min 多）
13. 點擊 "Gemini External Status Page" link
    → Google Cloud Status: "Gemini API elevated latency (60% of requests)"
    → 外部故障確認

on-call 決策：「這是 Gemini 側的故障，非我們的系統問題。」
- 動作A（短期）：啟動 fallback 模型 → `fallback_provider="palm"`，看 Panel 13
- 動作B（通知）：發通知給 product 團隊：「Gemini 外部故障中」
- 動作C（度量）：標記此時段為 "external incident"，不計入我們的 SLO burn
```

### 確認故障不在其他層
```
14. 驗證 Infrastructure（層級五）：
    - CPU: 42% ✓ 不是瓶頸
    - Memory: 62% ✓ 正常
    - Connections: 45/100 ✓ 充足
    → 底層資源不是根因

15. 驗證 GPU（層級六）：
    - GPU util: 62% ✓ 尚未飽和
    - Queue: 42 requests ✓ 短隊列
    - Batching: 78% ✓ 有效
    → GPU 不是根因，model 慢純粹是 Gemini provider 問題
```

### 路徑完整性檢查

| 層級 | Panel | Owner | 故障判斷 | Drill-down 目標 | 下一步 |
|------|-------|-------|---------|----------------|-------|
| 層級一 | Good Outcome SLI | @oncall-ai-platform | 有無影響使用者 | Service Overview | Panel 4 |
| 層級一 | API Latency P95 | @oncall-api | 有無違 SLO | Service Overview | Panel 4 |
| 層級二 | Golden Signals | @oncall-service-owner | 是慢是爛是卡 | API Breakdown | Panel 5/6 |
| 層級三 | Prompt Build & Retrieval | @oncall-workflow | 初期步驟有無問題 | Trace Search | Panel 14 |
| 層級三 | Model Chat & Tool | @oncall-workflow | 核心流程有無問題 | Trace Search | Panel 14 |
| 層級三 | Answer Validation | @oncall-quality | 品質有無問題 | Quality Logs | Panel 8 或 9 |
| 層級四 | Gemini Provider | @oncall-platform | 外部服務有無故障 | Google Status Page | Fallback/Notify |
| 層級四 | Retrieval Service | @oncall-retrieval-svc | 內部服務有無問題 | Service Logs | 根因排除 |
| 層級五 | CPU & Memory | @oncall-infra | 資源有無耗盡 | Container Restarts | 根因排除 |
| 層級五 | Network & Pool | @oncall-infra | 連線有無限制 | Network Stats | 根因排除 |
| 層級六 | GPU & Queue | @oncall-mlops | 加速器有無過載 | GPU Scaling | 降級或擴容 |
| 層級六 | Model Route | @oncall-mlops | 路由有無最優 | Routing Config | 根因排除 |

---

## Dashboard 設計驗收清單

根據 [Day24/Day24.md 第④節驗收](../Day24.md#④-sre-lab今日-diy用文字設計一份六層-dashboard-草圖)：

- [x] **六層各自有明確讀者，沒有把成因層指標直接放進第一層**
  - 層級一：only SLI / P95 / Error rate（使用者感受）
  - 層級二：Golden Signals（聚合黑盒子）
  - 層級三：RED by step（找到慢的步驟）
  - 層級四：external/internal deps（確認內外責任）
  - 層級五：CPU/Memory/Network（基礎資源）
  - 層級六：GPU/Queue（AI 特定）
  - 層級一絕無 CPU、Memory、Queue 這類成因級指標

- [x] **每個項目都有問題、owner、drill-down，答不出下一步的項目已被刪除**
  - 14 個 panel，每個都有清楚的「為什麼要看」
  - 每個都標註 owner（哪個團隊負責）
  - 每個都有 link 或下一步目標
  - 無孤立的指標（沒有無法解釋其異常的 panel）

- [x] **敏感與高基數資料（prompt、request_id）不在 metrics panel，只在 trace 裡查**
  - Panel 1-13 完全不含 prompt、user_id、API key
  - request_id 只出現在 Panel 14（trace sample），用於逐筆診斷
  - 所有 metrics 都用低基數 label（step、route、status）

- [x] **文件草圖尚未接上任何真實監控資料，也沒有驗證過任何一個 panel**
  - 本 dashboard.md 是純文字設計，無 Grafana JSON、無 PromQL 執行
  - 所有「Current:」欄位都是模擬值（用於說明「看到什麼時意味著什麼」）
  - 沒有接上真實 Prometheus 或 Tempo
  - 驗證只是「邏輯是否完整」，不是「數字是否真實」

---

## 後續步驟（非本 DIY 範圍）

本文未實作以下內容：

1. **Grafana Dashboard JSON**：實際 Grafana 配置、panel layout、color scheme
2. **PromQL 執行**：真實查詢的驗証、cardinality 測試、query performance
3. **告警規則**：每個 threshold 對應的 alert rule、通知路由、on-call 排程
4. **SLO 報告**：28 天 SLO 計算、error budget 定義、burn rate 驗証
5. **Runbook 連結**：具體故障時的操作步驟、rollback 程序、擴容決策
6. **Trace Backend 驗証**：Tempo/LangSmith 是否真能支撐 drill-down query
7. **團隊 Review**：on-call 同事是否同意此流程、是否需要調整讀者或決策

若要升級為 production dashboard，需依次補齊上述項目，並請工程師、SRE、MLOps 團隊各自 review 自己負責的層級。
