# Failure Mode Cards for Day11 DIY

對應 Day11.md 第 ④ 節「failure-mode card：先寫一句可驗證的敘述」的實踐。

---

## Card 1: Policy Provider Timeout

**故障模式**: Timeout（傳統生產環境）

**觸發條件**:
- Policy provider 在 250 ms 的 client deadline 內沒有回應
- 可能原因：provider 過載、網路延遲、連線池耗盡、DNS 問題

**Error**:
- `asyncio.TimeoutError` in application code

**使用者影響**:
- `/ask` 不回傳未驗證的答案（不誤導）
- 若沒有合格 cache fallback，回暫時不可用（HTTP 503）
- 使用者知道系統無法完成，而不是卡住

**偵測** (可觀測訊號):
- `dependency_timeout` 事件 log，含 `elapsed_ms` vs `timeout_ms`
- `/ask` 端點的 timeout 請求數統計（structured log 中 event=dependency_timeout）
- Trace 中的 `dependency.timeout` 事件

**立即減傷措施**:
1. 停止新 rollout；保留 interactive request 的容量
2. 若有可驗證的快取（<1 分鐘），回 degraded response 並標記 `degraded: true`
3. 明確回 503，而非假裝成功

**不可做的動作**:
1. ❌ 每一層都 retry（會乘法放大）
2. ❌ 因為不想回 503 而編造 fallback 答案
3. ❌ 無限延長 client timeout（只是延後故障）

**降級策略**:
- 若有版本化、可驗證、一天內更新過的唯讀快取，回應時標記：
  ```json
  {
    "answer": "Remote work requires manager approval.",
    "answer_status": "answered",
    "technical_success": true,
    "degraded": true,
    "fallback_source": "policy-cache-v42",
    "fallback_age_seconds": 420
  }
  ```
- 但 `degraded: true` 必須可被監控與告警

**根本改進**:
- 檢視 provider 的 SLA 是否與產品承諾一致
- 評估 deadline 是否設定過短（考慮網路時延、連線建立、DNS lookup）
- 考慮 circuit breaker 或 adaptive timeout

**驗證方式**:
- `curl .../ask` with `failure_mode=slow`
- 確認回應為 HTTP 503，`answer_status: "unavailable"`
- 檢查日誌中 `dependency_timeout` 事件與 `elapsed_ms` 值
- 確認沒有 `answer_status: "answered"`（不混淆使用者）

---

## Card 2: Policy Provider Unavailable (Connection Error)

**故障模式**: Dependency Unavailable

**觸發條件**:
- Policy provider 服務完全不可用或拒絕連線
- 可能原因：服務崩潰、DNS 故障、網路分割、權限問題

**Error**:
- `ConnectionError` or `TimeoutError` on connection attempt

**使用者影響**:
- 無法取得任何回答，明確提示「服務暫時不可用」

**偵測**:
- `dependency_connection_error` 事件 log
- Provider endpoint 健康檢查失敗
- Trace 中的 connection error

**立即減傷措施**:
1. 停止向 provider 發送新請求（fail fast）
2. 若 retry budget 存在且有效，**最多一次重試**（不是無限）
3. 之後明確回 503

**不可做的動作**:
1. ❌ 無限 retry（會對已經過載的服務補刀）
2. ❌ 多層都 retry（乘法放大，見 GitHub 2026-08-17 事故）
3. ❌ 編造答案避免 503

**Retry 策略**:
- Retry owner：**唯一在 application 層**
- Retriable condition：`ConnectionError`, `TimeoutError` only
- Max retries per request：1 次（總共 2 attempts）
- Backoff：exponential with jitter（避免 retry storm）
- Deadline check：確認在 request deadline 前完成

```
Example flow:
Attempt 1: ConnectionError
  ↓ (check deadline, add jitter delay)
Attempt 2 after 50ms: ConnectionError
  ↓
Fail with HTTP 503
```

**降級策略**:
- 同 Card 1 的快取機制
- 或完全拒絕（無合格降級方案）

**根本改進**:
- Investigate provider health（logs, metrics, alerting）
- Multi-provider failover strategy
- Health check probe frequency 優化

**驗證方式**:
- `curl .../ask` with `failure_mode=unavailable`
  - Expect: HTTP 503，單一 attempt
- `curl .../ask/with-retry` with `failure_mode=unavailable`
  - Expect: HTTP 503，最多 2 attempts，各 attempt 間有 log 記錄

---

## Card 3: Configuration / Deployment Error

**故障模式**: Configuration (Bad Change)

**觸發條件**:
- 新 deployment 中 provider endpoint 指向錯誤網域
- 或 API key scope 不足
- 或 feature flag 打開了實驗性未驗證的邏輯

**Error**:
- 通常表現為 connection/timeout，但伴隨 deployment version 變化

**使用者影響**:
- Deploy 後立即或逐漸出現高失敗率
- 表面看起來像「dependency timeout」或「overload」，實際是設定問題

**偵測**:
- 關聯欄位：`deployment_id`, `service_version`, `feature_flag_version`
- 時間線相關性：error spike 與 deploy/flag 更新完全同步
- Provider 端沒有異常（健康狀態正常）

**立即減傷措施**:
1. **先 rollback 或關閉 flag**（往往比擴容更快修復）
2. 不要先加 worker（會把更多流量打到錯誤配置）

**不可做的動作**:
1. ❌ 看到 error 就直接擴容（只是放大錯誤的範圍）
2. ❌ 無限重試（重試時還是打到錯誤 endpoint）

**降級策略**:
- 不適用；應該是立即 rollback

**根本改進**:
- Canary deployment：新 config 先測 1% 流量
- 自動化驗證：部署後自動 smoke test
- Feature flag rollout：新 logic 分批灰度

**驗證方式**:
- 記錄 `deployment_id` 在 structured log 的 resource attributes
- 觀察 error rate 與 deployment 時間線的相關性
- 若 rollback 後 error rate 立即下降，確認是 config 問題

---

## 使用提示

- 這三張卡對應 Day11.md 第 ⑨ 節「練習 C：寫一張你自己的 failure-mode card」
- 讀者應針對自己的系統依此範本補充其他 dependency（database、queue、external API 等）
- Card 的價值不在於預測所有根因，而在於提前定義：
  - 誰會看見什麼（使用者影響）
  - 系統要少做什麼（減傷措施）
  - 何時要直接拒絕（何時不該 retry）
