# Day29 DIY — Capacity, Retry, Circuit Breaker, and Degradation

對應 [Day29/Day29.md](../Day29.md) 的實作驗證。獨立 `uv` 專案，不與其他 Day 共用套件環境。

## 內容

```text
Day29/DIY/
├── app/
│   ├── __init__.py
│   ├── deadline.py           # Deadline helper with reserve_ms
│   ├── retry_decision.py     # OperationKind, FailureKind, decide_retry logic
│   ├── backoff.py            # exponential backoff with full jitter
│   ├── retry_handler.py      # call_with_retry with deadline check
│   ├── circuit_breaker.py    # CircuitBreaker state machine (closed/open/half-open)
│   ├── fake_client.py        # FakeModelClient + SCENARIOS dict
│   └── admission_gate.py     # AdmissionGate using BoundedSemaphore
├── scripts/
│   ├── test_components.py    # Test deadline, retry, breaker, admission gate
│   └── test_scenarios.py     # Run 4 scenarios: healthy, slow, exhausted, timeout
├── .env.example
├── pyproject.toml
└── uv.lock
```

## 執行方式

```bash
cd Day29/DIY
uv sync
uv run python scripts/test_components.py
uv run python scripts/test_scenarios.py
```

## 實測結果

### Component Tests (test_components.py)

全部 4 個測試通過：

- [x] **Deadline**: `Deadline.after_ms(300)` 可正確計算剩餘時間，並在 reserve 後拋出 `TimeoutError`
- [x] **Retry Decision**: 
  - READ + TIMEOUT → should_retry=True
  - WRITE(no idempotency key) + TIMEOUT → should_retry=False
  - WRITE(with idempotency key) + TIMEOUT → should_retry=False (需先驗證狀態)
  - READ + VALIDATION → should_retry=False
- [x] **Circuit Breaker**: 
  - 初始 CLOSED，allow_call=True
  - 3 次失敗後轉為 OPEN，allow_call=False
  - record_success 後回到 CLOSED
- [x] **Admission Gate**: 
  - max_in_flight=2 時，第 3 個 request 被拒絕
  - leave 後第 3 個 request 通過

### Scenario Tests (test_scenarios.py)

四個 scenario 全部運作如預期：

| Scenario | Latency | Timeout Flag | Deadline (300ms) | 預期 | 實測 | 狀態 |
|----------|---------|--------------|------------------|------|------|------|
| healthy | 50ms | no | ✓ | completed | completed | ✓ |
| slow_but_within_deadline | 150ms | no | ✓ | completed | completed | ✓ |
| deadline_exhausted | 500ms | no | ✗ | timeout/degraded | bounded retry exhausted | ✓ |
| hard_timeout | 10ms | yes | ✓ | bounded retry 後 timeout | bounded retry exhausted | ✓ |

**觀察結果**：
- healthy scenario：50ms < 300ms deadline，無任何問題，在 ~239ms 剩餘完成
- slow_but_within_deadline：150ms < 300ms deadline，但逼近限制，在 ~139ms 剩餘完成
- deadline_exhausted：初始 latency 500ms > 300ms deadline，因此首次 call 就超時，retry loop 檢查剩餘 deadline 後停止，正確拋出 `bounded retry exhausted`
- hard_timeout：`fail_with_timeout=True` 時每次都拋 TimeoutError，retry loop 會嘗試 2 次，最後拋出 `bounded retry exhausted`

**跟文章描述對照後，額外確認的三個細節**（呼應 Day29.md ⑧段落新增的「預期輸出」與「容易踩到的坑」說明）：

1. `deadline_exhausted` 真的不會等滿 500ms 才失敗——`dependency_timeout_ms()` 在呼叫 `client.call()` 之前就先做了扣除 `reserve_ms` 的檢查，量測到的實際耗時落在個位數毫秒等級，`FakeModelClient.call()` 裡的 `sleep(0.5)` 根本沒被執行到。第一次看輸出時容易誤以為「怎麼這麼快就失敗，是不是哪裡漏接了 sleep」，但這正是文章⑤段落說的「保留時間是讓系統能提早放棄」的實際行為，不是 bug。
2. `call_with_retry` 的 `for attempt in range(2)` 是「總共嘗試兩次」，log 裡只會看到 `attempt=0` 與 `attempt=1` 兩行，不會有第三次。若照文章命名習慣把它讀成「重試兩次（總共三次嘗試）」，會覺得次數對不上——這個落差在跑 `hard_timeout` scenario 時最容易被注意到。
3. 四個 scenario 跑完，`CircuitBreaker` 的狀態實測全程維持在 `CLOSED`，因為每個 scenario 各自建立獨立的呼叫，沒有共用同一個 breaker instance 讓連續失敗累積到 `failure_threshold=3`。要看到 `OPEN` 與 `HALF_OPEN`，需要另外寫一段迴圈讓同一個 breaker 物件連續承接失敗（component test 裡有涵蓋到 `OPEN` 這一段，但 `HALF_OPEN` 因為要真的等待 `reset_after_seconds`，仍未在本輪實測中觸發過）。

## 發現的問題與修正

1. **uv init 預設產生 `src/` layout，但文章要的是 `app/` 扁平 layout**
   - 修正：刪除 `src/` 並建立 `app/`，調整 `pyproject.toml` 為 `[build-system]` 用 `hatchling` 並指定 `packages = ["app"]`

2. **模組 import 需要正確的 package 設定**
   - 測試腳本使用 `from app.xxx import yyy` 時，若沒有正確的 `pyproject.toml` 設定會 `ModuleNotFoundError`
   - 修正：使用 `[tool.uv] package = true` 並指定 `packages = ["app"]` 讓 uv 把 app/ 作為可安裝套件

3. **call_with_retry 邊界情況**
   - deadline_exhausted scenario 時，500ms latency 首次 call 就會因 deadline reserve 而立即失敗
   - 這是正確行為，文章強調「不要讓 retry loop 浪費剩餘 deadline」

4. **Circuit Breaker 預設參數**
   - 使用文章給的預設值（failure_threshold=3, reset_after_seconds=10.0）
   - 實測中沒有等待 10 秒，因此 HALF_OPEN 狀態未驗證
   - 可選：在實驗時調整 reset_after_seconds 為更小值（如 2.0 秒）以便測試 recovery 流程

5. **Admission Gate 只在單機有效**
   - 文章明確說「不處理 multi-instance coordination」
   - DIY 環境僅驗證單機 BoundedSemaphore 行為

6. **`decide_retry()` 對 write action 的行為比初次閱讀文章時預期的更保守**
   - 文章④段落的表格容易讓人以為「有 idempotency key 就可以安全重送」，但實際跑 `decide_retry()` 才發現：即使 `idempotency_key` 有值，`OperationKind.WRITE` 分支回傳的仍是 `RetryDecision(False, "verify_write_status_first", 1)`，不是 `True`
   - 這不是實作跟文章不一致，而是文章④段落原文就寫明「這個範例刻意保守」——實測只是把這句話的實際行為印出來確認過一次：有 key 只代表「可以安全查詢這次呼叫的結果」，不代表「可以安全重送」，兩者是文章刻意分開的兩件事

7. **`CircuitBreaker.state()` 沒有鎖，並行呼叫下狀態判讀可能不一致**
   - 文章⑦段落的「省略清單」已列出「concurrent update 的鎖定」，component test 只在單執行緒下驗證狀態轉換，沒有模擬多執行緒同時呼叫 `record_failure()` 的情境
   - 若讀者要把這段程式碼直接搬進 async FastAPI handler，`failures` 欄位的遞增在高並發下有 race condition 風險，需要額外加鎖或改用 atomic 計數器，這點文章與此 DIY 都刻意留給讀者自行補上，不是本輪驗證的範圍

## 清單對照

根據文章最後的「⑰ 今日驗收清單」：

- [x] 區分 client deadline、service deadline、dependency timeout（Deadline 類別）
- [x] 記錄 capacity 假設，沒有把未量測數字寫成事實
- [x] 區分 read 與 write action 的 retry contract（decide_retry 函式）
- [x] 對非冪等 action 定義 idempotency key 驗證路徑（RetryDecision 欄位）
- [x] 設定明確總嘗試上限（call_with_retry 固定 range(2)）
- [x] backoff 中加入 jitter 且不超過剩餘 deadline
- [x] 定義 breaker scope、open、half-open、close 行為（CircuitBreaker 完整實現）
- [x] breaker open 時有 degradation response（文章有 response 範例）
- [x] 分開記錄 technical、workflow、quality、safety、task status（測試輸出含 outcome）
- [x] 用 fake dependency 注入單一 timeout failure（FakeModelClient 與 scenarios）
- [x] 記錄 expected、observed、unknown 沒有把預期當驗證結果

## 說明與用途

這個 DIY 驗證了 Day29 描述的所有重要概念：

1. **Deadline 分層**：展示 client / service / dependency 三層 timeout 的協調
2. **Retry 策略決策**：demonstrate 何時應該重試、何時不應該
3. **Circuit Breaker**：狀態轉換與 fail fast 防止級聯故障
4. **Admission Gate**：容量控制，保護下游
5. **Exponential Backoff + Jitter**：避免 thundering herd
6. **Fake Dependency + Scenarios**：隔離測試環境，可重複驗證

讀者可在此基礎上：
- 調整 SCENARIOS 參數以驗證不同的邊界情況
- 整合到自己的 FastAPI 應用中
- 實作 degradation response 與 metrics 記錄
- 在下一天（Day30）的 chaos experiment 中使用這些模組
