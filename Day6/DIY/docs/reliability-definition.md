# Reliability Definition

> Status: 練習用文件。填入的是本 Lab 目前能提出證據或誠實標記 `UNKNOWN` 的內容，不是已驗證的 production SLO。

## User Task

使用者送出問題後，在可接受時間內取得可用回答。

（對應 [Service Reliability Charter](service-reliability-charter.md) 第 3 節 User Expectations：「正常 request 取得格式明確且可理解的 response；異常時得到有限時間內的明確錯誤，而不是無限等待」）

## Request Boundary

- 入口：`GET /api/demo`（本 Lab 目前唯一非故障注入的核心 endpoint；`sre-for-ai-era` production 版本應改為實際的 `POST /api/ask`）
- 起點：使用者送出 request（client 發出 HTTP request 的時間點，非 server 收到的時間點）
- 終點：使用者收到完整回應，或明確收到可採取下一步的失敗訊息（例如 `503 Database unavailable`）
- 關鍵依賴：FastAPI process、PostgreSQL（`/api/database` 路徑）；Redis、LLM provider、retriever 目前尚未整合進 request 路徑

## Availability

- 納入哪些 request：`/api/demo`、`/api/database` 等使用者可能實際呼叫的 `/api/*`；排除 `/health`、`/ready`、`/metrics`
- 成功定義：在 timeout 之內回傳非 5xx 狀態碼，且 response body 符合 endpoint 既有 schema
- 失敗定義：5xx、client 端已放棄的 timeout（即使 server 事後仍回 200）、依賴不可用導致無法完成任務
- 排除條件：內部 readiness probe、已知的測試流量、使用者主動取消的 request
- 目前證據：Day 3 的故障注入實驗已用 `docker compose stop postgres` 重現 `/api/database` 回 503 的行為，並留有對應 log 與 trace；長期 Availability 百分比目前為 `UNKNOWN`

## Latency

- 從哪裡量到哪裡：目前只量到 server 端 `request_context_middleware` 記錄的 `duration_ms`；client 端等待時間尚未量測
- 可接受 latency：延續 Charter 假設 P95 < 300 ms；`UNKNOWN`，待使用者研究或長期 baseline 驗證
- 是否區分 first token 與完整回應：否；本 Lab 尚未整合會逐步輸出 token 的 LLM 呼叫
- 目前 evidence：`HTTP_REQUEST_DURATION_SECONDS` histogram（見 `app/metrics.py`）已在跑，可用 `histogram_quantile` 查詢 P95；尚未累積足夠流量做出有意義的長期判斷

## Correctness

- 哪些規則可以自動驗證：`/api/demo` response 必須含 `message` 與 `timestamp` 兩個欄位；`/api/database` 成功時 `result` 必須等於 `1`（`SELECT 1` 的預期值）
- 哪些需要 evaluator 或人工審閱：本 Lab 目前沒有 AI 生成內容，尚無此類項目；未來加入 LLM 回答後需要
- Technical success 與 correctness 如何分開記錄：目前只記錄 HTTP status code 與 duration，尚未把「schema 正確」與「內容正確」拆成獨立指標——這正是本篇（Day6 ④）指出的落差，本 Lab 目前也還沒做到
- 目前 evidence：手動 curl 驗證過 `/api/demo` 與 `/api/database` 的正常回應格式；沒有自動化 contract test，`UNKNOWN`

## Durability

- 要保留的資料：目前 PostgreSQL 只跑 `SELECT 1`，沒有寫入任何使用者資料；未來若接上對話紀錄，需要保留 request/response 記錄
- 可接受的資料遺失範圍：UNKNOWN
- 備份或保留機制：目前沒有為 `postgres` 這個 Docker volume 設定任何備份；`docker compose down -v` 會直接清空資料，這件事本身就是需要標記的風險
- 已驗證的 restore：UNKNOWN——沒有備份，也就沒有 restore 可以演練

## Recoverability

- 可接受恢復時間：UNKNOWN
- 可接受資料損失時間範圍：UNKNOWN
- 已演練的恢復步驟：Day 3 已演練「`docker compose stop postgres` 後再 `start postgres`，確認 `/api/database` 恢復回傳 `200`」與「`docker compose kill -s SIGKILL api` 後容器自動重啟，確認 `/health` 恢復」；兩者都只驗證了「服務恢復」，沒有驗證「資料恢復」，因為目前沒有需要復原的資料
- 恢復後的驗證方式：重新呼叫對應 endpoint，並確認 Prometheus `up`、log 與 trace 都回到正常狀態

## Open Questions

- 哪些 failure 對使用者是不可接受的？目前假設「無限等待」與「靜默回傳錯誤資料」最不可接受，但沒有使用者研究佐證。
- 哪一個依賴失敗會讓這項任務無法完成？目前只有 PostgreSQL 一個外部依賴會直接讓 `/api/database` 失敗；未來加入 LLM provider 後，這條清單會變長。
- 現有 Metrics、Logs、Traces 缺少什麼 evidence？缺少 client 端等待時間、缺少「內容正確」的判斷依據、缺少任何形式的資料備份與 restore 演練證據。
