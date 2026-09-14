# Service Reliability Charter

> Status: Initial hypothesis for the learning lab. This is not a production SLA and does not claim that the goals below have been achieved.

## 1. Service Overview

- 服務名稱：AI SRE Lab API
- 服務用途：提供可觀測、可注入故障的 FastAPI 服務，支援後續 AI Workflow reliability 實驗
- 主要使用者：開發者、系列讀者與自動化測試工具
- 核心使用者任務：提交 API request，取得可理解的回應，並能在異常時辨識結果與故障狀態

## 2. System Boundary

- 入口：FastAPI HTTP API
- 目前主要依賴：PostgreSQL、Redis
- Observability 依賴：Prometheus、Loki、Tempo、OpenTelemetry Collector、Grafana、Alloy
- 未來主要依賴：LLM provider、Retriever、Vector Database、Tool API
- 非核心依賴：本機 Docker Compose 與用於查詢觀測資料的 UI
- 不在本服務目前負責範圍內的項目：Cloud infrastructure、DNS、TLS termination、Authentication、Multi-region failover、Production backup、第三方 LLM 的內部可用性

目前邊界：

```text
Client
  ↓
FastAPI
  ├─ PostgreSQL
  ├─ Redis
  └─ Observability Stack
       ├─ Prometheus
       ├─ Loki
       └─ Tempo
```

未來 AI Workflow 邊界：

```text
Client → FastAPI → Prompt → Retriever → Model → Tool → Validator → Response
```

## 3. User Expectations

- 使用者期待：正常 request 取得格式明確且可理解的 response；異常時得到有限時間內的明確錯誤，而不是無限等待
- 可接受的回應時間：一般非故障注入 API 先以 P95 小於 300 ms 作為練習假設；尚未用長期資料驗證
- 不可接受的失敗類型：無限等待、靜默回傳錯誤資料、依賴故障卻宣告完整 Ready、無法關聯 request 的錯誤、恢復後未驗證即宣告完成
- 未來 AI 使用者期待：回答應可追蹤使用的 Model、Prompt 與 Workflow steps；需要知識庫內容時，答案應有可驗證的根據

## 4. Reliability Dimensions

- Availability：使用者需要的 API endpoint 可接受 request 並回傳預期類型的 response
- Latency：成功不能只看 status code；response 必須在使用者可接受的時間內完成
- Correctness：response schema、status code 與資料必須符合 endpoint contract；未來還需驗證 AI task result
- Recoverability：Container 或 Dependency 異常排除後，服務能恢復，並由新的 request 驗證
- Data durability：目前 Lab 沒有定義正式 durability 目標；PostgreSQL volume 刪除後的資料恢復能力為 UNKNOWN

## 5. Known Failure Modes

| Failure mode | 可能的使用者影響 | 目前可見證據 | 初始處置或驗證 |
|---|---|---|---|
| Application exception | HTTP 500 | Error metric、exception log、error trace | 修復後重新呼叫 endpoint |
| Dependency timeout | 等待過久或 client 放棄 | Latency histogram、duration log、span duration | 設定 timeout；確認 client 與 server 兩側結果 |
| PostgreSQL unavailable | Database endpoint 回 503 | Endpoint status、log、trace | 恢復 PostgreSQL 後重新查詢 |
| Container crash | 連線失敗；Prometheus scrape target down | Container exit state、Prometheus `up` | 重啟後驗證 `/health` 與關鍵 endpoint |
| Resource exhaustion | Process 被 OOM kill、request 中斷 | Exit code、OOMKilled state、scrape gap | 限制資源；恢復後重新驗證 |
| Configuration error | 啟動失敗或依賴連線失敗 | Startup log、container state | 修正設定並執行 smoke test |
| Network failure | Timeout、connection refused 或部分 dependency failure | Client result、log、trace gap | 驗證 DNS、connectivity、timeout 與 recovery |

## 6. Initial Observability

- Metrics：HTTP request count、status count、request duration histogram、in-progress request gauge、Prometheus target `up`
- Logs：JSON structured logs、Request ID、method、path、status code、duration、exception stack trace
- Traces：HTTP request trace、status、duration、Trace ID；目前尚未涵蓋真正的 LLM/RAG/Tool spans
- Dashboards：Grafana 作為 Prometheus、Loki 與 Tempo 的調查入口
- 已知缺口：目前沒有長期 retention、正式 alert rule、SLO dashboard、真實使用者流量或 AI quality evaluation

## 7. Initial Reliability Goals

- Availability goal：先建立 baseline；後續以 99.5% request success rate 作為練習目標，不宣稱已達成
- Latency goal：一般非故障注入 API 以 P95 小於 300 ms 作為練習目標，不宣稱已達成
- Error handling goal：已知 dependency failure 應在有限時間內回傳明確狀態；不得無限等待或以成功 response 隱藏失敗
- Recovery expectation：執行恢復動作後，必須以新的 user-facing request 與至少一種 telemetry 驗證；正式 RTO 目前為 UNKNOWN
- Review trigger：新增關鍵 dependency、變更核心 user journey、累積足夠 baseline 或發生新 failure mode 時更新本文件

## 8. AI Era Extension

- 使用的模型：目前 Day 4 Lab 尚未整合；未來 provider 與 model 為 UNKNOWN
- 是否使用 RAG：目前否；未來規劃加入
- 是否有 Tool Calling：目前否；未來規劃加入
- Technical success 如何定義：API 與 Workflow steps 在限制時間內完成，schema 與 status 符合 contract，所需 dependency 可用
- Task success 如何定義：使用者取得足以完成目標、且符合題意與必要限制的答案或操作結果
- 語意品質如何評估：建立 task-specific golden dataset，結合 deterministic checks、人工評估與經人工標註校準的 model-based grader
- 安全風險：Prompt injection、敏感資料外洩、未授權 Tool Call、不安全輸出、Evaluator 偏差
- 成本限制：需追蹤 Token Cost、Retry Amplification 與 Cost per Successful Task；初始預算為 UNKNOWN

候選 Operational Metrics：

```text
TTFT
Token Throughput
Provider Error Rate
Retriever Empty-result Rate
Tool-call Success Rate
Queue Backlog
Retry Amplification
```

候選 Task、Quality 與 Safety Metrics：

```text
Task-success Rate
Groundedness Score
Safety Violation Rate
Instruction-following Score
Cost per Successful Task
```

## 9. Open Questions

1. 哪一個 user journey 應該成為第一個正式 SLI 的分母：所有 HTTP requests，還是只有有效的 `/api/demo` requests？
2. P95 小於 300 ms 是否符合真實使用者期待？目前只有短時間 Lab baseline，沒有真實流量證據。
3. 當 LLM provider 回 HTTP 200，但答案沒有根據或無法完成任務時，如何建立可重複的 failure label？
4. Golden dataset 應涵蓋哪些正常案例、edge cases、Prompt Injection 與 dependency failures？
5. Model-based grader 要如何用人工標註校準，才能避免把 grader 的偏差當成 service quality？
6. 哪些 AI quality 或 safety 異常應觸發 Pager，哪些只需要建立 ticket 或離線調查？
7. 在不同 Model、Fallback 與 Retry 策略之間，Latency、Quality、Safety 與 Cost 的可接受邊界是什麼？
8. PostgreSQL 資料的 durability、backup 與 restore 目標是什麼？目前為 UNKNOWN。

## 10. Evidence Boundary

- Day 2 已建立 Metrics、Logs、Traces 與 Grafana 查詢入口。
- Day 3 已在本機驗證 Slow Request、Client Timeout、HTTP 500、PostgreSQL unavailable、SIGKILL 與 OOM recovery。
- 上述實驗只證明特定本機環境與特定時間點的行為，不等同 Production reliability、SLO achievement 或長期 Availability。
- `99.5%` 與 `P95 < 300 ms` 是後續學習用 Hypothesis；必須先定義 measurement window、eligible events 與 bad events，才可能成為可執行的 SLO。
