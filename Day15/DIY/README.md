# Day15 DIY — Availability：不是把 200 數一數

對應 [Day15/Day15.md](../Day15.md) 的實作驗證。獨立 `uv` 專案，與其他 Day 完全分開。

## 內容

```text
Day15/DIY/
├── app/
│   ├── __init__.py
│   ├── availability.py    # SLI classifier with SliResult enum
│   └── metrics.py         # Prometheus Counter + record_sli_event()
├── tests/
│   ├── __init__.py
│   └── test_availability.py   # pytest fixtures with parametrize
├── scripts/
│   └── validate_denominator.py # Step 4: Two-scenario traffic validation
├── .env.example
├── .python-version
├── pyproject.toml
└── uv.lock
```

## 執行方式

### 1. 環境設定

```bash
cd Day15/DIY
uv sync
```

### 2. 執行測試

```bash
uv run pytest tests/test_availability.py -v
```

預期結果：10 個 fixture 全部通過

```text
tests/test_availability.py::test_classify_availability[event0-True-SliResult.GOOD-contract_satisfied] PASSED
tests/test_availability.py::test_classify_availability[event1-True-SliResult.GOOD-contract_satisfied] PASSED
tests/test_availability.py::test_classify_availability[event2-True-SliResult.GOOD-contract_satisfied] PASSED
...
Pytest: 10 passed
```

### 3. 驗證分母正確性

```bash
uv run python scripts/validate_denominator.py
```

預期結果：情境 A 的 availability 為 80%（8 good / 10 valid），情境 B 的 5 筆 invalid request 不進分母

```text
Scenario A Results:
  Good: 8
  Bad: 2
  Excluded: 0
  Denominator (valid): 10
  Availability: 8/10 = 80.0%

Scenario B Results:
  Excluded: 5
  ✓ Invalid requests correctly excluded from denominator
```

## 實測結果

逐項對照文章 Day15 的驗收標準（⑧ DIY 驗收清單）：

### ✓ SLO spec 清楚定義

`app/availability.py` 將產品決策集中在常數與 `classify_availability()` 函式：

- `GOOD_RESPONSE_STATUSES`: 明確列舉哪些狀態算「好結果」（completed、insufficient_context、requires_human_review）
- `MAX_LATENCY_MS = 10_000`: Service level objective 的延遲上限
- `AvailabilityEvent` 與 `Classification` dataclass：分離輸入事件與分類結果
- `SliResult` enum：三種明確的分類結果（GOOD、BAD、EXCLUDED）

### ✓ Classifier 對各種情況有 fixture

`tests/test_availability.py` 用 pytest parametrize 涵蓋 10 個場景：

1. **正常完成**: valid_request=True, latency=230ms, contract_valid=True, status="completed" → GOOD
2. **誠實拒答 (insufficient_context)**: 同上但 status="insufficient_context" → GOOD
3. **誠實拒答 (requires_human_review)**: 同上但 status="requires_human_review" → GOOD
4. **逾時**: latency=10_001ms（超過 MAX_LATENCY_MS）→ BAD (deadline_exceeded)
5. **Contract 失敗**: contract_valid=False → BAD (invalid_response_contract)
6. **Workflow 失敗**: status 不在 GOOD_RESPONSE_STATUSES 中 → BAD (workflow_failed)
7. **無效請求**: valid_request=False → EXCLUDED (invalid_request)
8. **無效且任意狀態**: valid_request=False 即使其他欄位正確 → EXCLUDED
9. **邊界值**: latency 恰好 10_000ms（不超過）→ GOOD
10. **誠實拒答但缺欄位**: contract_valid=False 且 status="insufficient_context" 同時出現 → BAD (invalid_response_contract)，驗證 `classify_availability()` 先檢查 contract_valid、再檢查 response_status 的判斷順序

### ✓ 判定由測試保護

所有分類規則都由 pytest fixture 保護。若修改 GOOD_RESPONSE_STATUSES 或 MAX_LATENCY_MS，測試會立刻失敗，強制開發者檢查「服務契約是否真的改了」。

### ✓ Metric label 低基數

`app/metrics.py` 的 `ask_sli_events_total` counter 只用三個 label：

- `sli_eligible`: "true" / "false" (2 個值)
- `sli_result`: "good" / "bad" / "excluded" (3 個值)
- `response_status`: "completed" / "insufficient_context" / "requires_human_review" 等固定列舉 (可控數量)

**不會** 放入 `request_id`、prompt、user_id 或 exception message，避免 cardinality 爆炸。

### ✓ 分母驗證

`scripts/validate_denominator.py` 演示 step 4 的兩個情境：

- **Scenario A**: 8 good + 2 bad (timeout) → denominator = 10，availability = 80%
- **Scenario B**: 5 invalid requests → excluded，**不改變** scenario A 的分母

輸出清楚顯示：

```text
Scenario A denominator: 10 (8 good + 2 bad)
Scenario B adds: 5 excluded
Combined denominator: 10 (NOT 15)
✓ Invalid requests correctly excluded from denominator
✓ SLI calculation: good / valid = 8 / 10 = 80%
```

### ✓ 無需外部服務

整個 DIY 專案完全獨立，不需要：

- FastAPI 或 HTTP server
- Prometheus 伺服器（只有 client library）
- 資料庫
- LLM API 或假的認證

### ✓ 程式碼對應文章

- `app/availability.py` 逐字對應文章「步驟 1」的 `classify_availability()`
- `tests/test_availability.py` 遵循文章「步驟 2」的 fixture 設計
- `app/metrics.py` 實現文章「步驟 3」的 `record_sli_event()` 與 counter
- `scripts/validate_denominator.py` 驗證文章「步驟 4」的分母假設
- 註釋與常數名稱維持一致，易於對照

### 實際執行輸出（2026-09-27 重跑）

`uv run pytest tests/test_availability.py -v` 實際輸出結尾：

```text
10 passed in 0.02s
```

第 10 個 fixture 是這次重跑新增的：`AvailabilityEvent(True, 280, False, "insufficient_context")`，也就是模型誠實回報「資訊不足」、但這次回傳的 JSON 本身缺了必要欄位。加入這個組合前,`classify_availability()` 的判斷順序（先看 `contract_valid`，再看 `response_status`）只在程式碼裡有註解說明，沒有任何一個 fixture 真正驗證過；現在若有人不小心把判斷順序反過來（先看 `response_status` 是否在白名單內，再看 `contract_valid`），這個 fixture 會立刻失敗，因為錯誤順序會讓這筆事件被誤判成 GOOD。

`uv run python scripts/validate_denominator.py` 的完整輸出與文章「步驟 4」的預期完全一致：Scenario A 算出 `8/10 = 80.0%`，Scenario B 的 5 筆 invalid request 全部落在 `excluded`，合併後的分母仍是 10，不是 15。這直接對照到文章第③、⑤節反覆強調的「有效請求」與「全部請求」分離——這個 DIY 的價值不在於程式碼有多少行，而在於它用一組可重跑的數字，把「別把 excluded 算進分母」從一句提醒變成一個會通過或失敗的斷言。

值得記錄的觀察：兩個腳本合計執行時間在本機不到 0.1 秒，說明這個 DIY 的核心邏輯本身極輕量——真正需要花時間驗證的，是把 `record_sli_event()` 接進一個真實跑著的 FastAPI route、串上 Day 2 的 Prometheus scrape 之後，資料流是否如預期般被記錄下來，而不是 classifier 本身的正確性（那已經由 10 個 fixture 保護住了）。

## 發現的問題與修正

### 無重大問題

文章的程式碼邏輯清楚、完整，實作過程中無遇到技術阻礙。這次重跑除了既有的 9 個 fixture 與兩個情境腳本，另外針對文章第⑧節點名的一個缺口補了第 10 個 fixture，結果與預期一致，沒有發現程式碼與文章擴寫後敘述對不上的地方。

### 細節澄清

1. **Pydantic 移除**: 原有的 DIY 用 pydantic 定義 Event model。文章重寫後改用標準庫的 dataclass，更輕量且足以表達需求。

2. **parametrize 覆蓋**: 原有 DIY 手寫 6 個 fixture。新的 pytest parametrize 先擴展到 9 個（加入邊界情況：latency 恰好在臨界值），這次重跑再補第 10 個，涵蓋「誠實拒答卻缺欄位」的組合。

3. **metrics.py 新增**: 文章「步驟 3」要求整合 Prometheus，故新建此模組。在實際 FastAPI 應用中，會在 `/ask` route 的最後呼叫 `record_sli_event()`。

### 已補上的坑：「誠實拒答卻缺欄位」

先前這裡記錄過一個缺口：9 個 fixture 裡沒有 `contract_valid=False` 且 `response_status="insufficient_context"` 同時出現的案例，也就是模型正確地拒答，但回傳的 JSON 本身缺了必要欄位。這次重跑已經在 `tests/test_availability.py` 補上第 10 個 fixture，實際跑出 `10 passed`，驗證了 `classify_availability()` 判斷順序的正確性（先看 `contract_valid`，再看 `response_status`）不再只是程式碼註解裡的說明，而是有一個會失敗的斷言在保護它。

### 這個 DIY 仍未涵蓋、但文章擴寫後特別提醒的坑

1. **`/metrics` 資料流沒有被這個 DIY 實際驗證過**：`app/metrics.py` 目前只在單元測試層級呼叫 `record_sli_event()`，沒有起一個真正的 FastAPI server 讓 Prometheus 去 scrape。若照文章「步驟 3」的敘述接上 Day 2 的 observability stack，第一次很可能會先卡在 target 沒被 scrape 到，而不是 classifier 邏輯本身——這與文章新增段落描述的「由外而內」排查順序（先確認 target UP，再查 label，最後才懷疑程式邏輯）一致，只是這個 DIY 目前還沒實際跑過這一段，留給下一次擴充時驗證。
2. **串流與 client-side completion signal 完全沒有實作**：文章「錯算三」擴寫後補了 SSE `event: done` 的具體設計，但這個 DIY 從一開始就是同步單一請求模型，沒有任何串流路徑，這一段的落地驗證仍待補上。
3. **recording rule 的 `interval` 設定沒有實測**：文章第⑤節新增了「為什麼 `interval` 要設 1 分鐘」的討論，但這個 DIY 完全沒有 Prometheus 伺服器,自然也沒有機會實際測出不同 `interval` 對 burn rate alert 偵測延遲的影響——這一段目前只能停留在文章的推導層次，等接上真正的 observability stack 才能驗證。

## 環境版本

- Python 3.14
- uv (latest)
- prometheus-client==0.26.0
- pytest==8.0.0 (via optional-dependencies)

## 限制與注意

- **Lab 合約**: `MAX_LATENCY_MS = 10_000` 是教材假設，非生產 SLO。實際值應由產品與 SRE 確定，並在 SLO spec（Day 14）記錄。
- **無 Prometheus 伺服器**: 此 DIY 只測試分類邏輯，不包含實際的 Prometheus scrape、PromQL query 與 dashboard。若要完整測試 metrics，需搭配 Day 2 的 observability stack。
- **無串流或非同步**: 實作假設單一同步請求。若應用使用串流回應，需額外設計 completion signal（文章有提及）。
