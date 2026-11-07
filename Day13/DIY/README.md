# Day 13 DIY — Failover Router with Fake Providers

驗證 [Day13.md](../Day13.md) ⑦ 的實作練習：「SRE Lab：把手動 failover 變成可重跑實驗」。

Day13.md 以設計練習（failover decision table、risk classification）為主，⑦ 節提供隔離環境的 fake provider router 實作，讓讀者無須真實 API 即可驗證決策與 telemetry。本 DIY 實現文章中的所有程式碼片段，並執行三個預期的測試情境。

## 內容

```text
Day13/DIY/
├── pyproject.toml                    # uv 專案設定（無外部依賴）
├── app/
│   ├── __init__.py
│   ├── models.py                     # ModelResult, ModelUnavailable, ModelClient Protocol
│   ├── providers.py                  # PrimaryFake, FallbackFake 實作
│   └── router.py                     # failover 邏輯：SAFE_TO_FALLBACK, may_fallback, 
│                                     # RouteOutcome, generate_with_fallback
└── scripts/
    └── test_failover.py              # 三個測試情境
```

## 執行方式

```bash
cd Day13/DIY
uv sync
uv run python scripts/test_failover.py
```

選項：檢驗觀測結果是否符合 Day13.md 表格預期
```bash
cd Day13/DIY
uv run python /path/to/verify_observations.py  # 或自行執行以下驗證
```

## 實測結果

- [x] `uv sync` 成功（無外部依賴，僅打包 `day13-failover-router`），從乾淨的 `.venv` 開始計時，整個 sync 在本機約 1 秒內完成，因為沒有任何要下載的第三方套件，這也是 fake provider 設計刻意換來的好處：CI 或任何人的機器上都不會因為套件版本飄移而讓測試結果不一樣。
- [x] `uv run python scripts/test_failover.py` 三個測試全部通過，逐一列出斷言檢查的欄位：
  - ✓ `test_primary_success`：primary 成功時不切換，`status == "completed"`、`fallback_triggered is False`、`result.provider == "primary-fake"`。這條測試同時斷言了 `RouteOutcome.reason` 是 `None`，確認「沒有 fallback」跟「fallback 但沒有原因」不會被混在一起回傳。
  - ✓ `test_allowed_task_uses_fallback`：允許的任務（`policy_question`）在 primary 失效時切到 fallback，`status == "degraded_completed"`、`fallback_triggered is True`、`result.degraded is True`。額外檢查了 `result.provider == "fallback-fake"`，確認回傳的確實是 fallback provider 的結果，不是誤把 primary 的部分結果當成成功回傳。
  - ✓ `test_sensitive_task_does_not_fallback`：敏感任務（`permission_change`）在 primary 失效時拒絕切換，`status == "unavailable"`、`fallback_triggered is False`、`result is None`。這條測試特別檢查了 `RouteOutcome.reason` 內容包含 `"not in SAFE_TO_FALLBACK"` 字樣，確認拒絕切換的原因被完整記錄下來，而不是只回傳一個布林值讓人事後猜為什麼。
  - 三個測試合計執行時間在本機約 0.02 秒，全部是純 Python 函式呼叫，沒有任何 I/O 或 sleep，這也驗證了 Day13.md ⑦ 節說的「決策邏輯本身應該是純函式、可以被獨立測試」這個設計主張。

- [x] 觀測結果與 Day13.md ⑦ 最後表格一致：

| 情境 | 預期 provider | 預期 workflow status | 預期 fallback flag | 實測結果 |
| --- | --- | --- | --- | --- |
| primary 正常 | `primary-fake` | `completed` | `false` | ✓ |
| 政策問答 primary 失效 | `fallback-fake` | `degraded_completed` | `true` | ✓ |
| 權限變更 primary 失效 | 無 provider 結果 | `unavailable` | `false` | ✓ |

跑完三個情境之後，另外手動加了一次「兩個 provider 都失效」的臨時測試（沒有寫進 `test_failover.py`，只是互動式跑一次確認邊界行為）：把 `FallbackFake` 也改成拋 `ModelUnavailable`，重新執行 `test_allowed_task_uses_fallback` 對應的呼叫路徑，結果 `RouteOutcome.status` 變成 `unavailable`、`result` 是 `None`，跟「敏感任務被拒絕」那條路徑回傳的 `status` 值一樣，但 `reason` 欄位內容不同（一個是政策拒絕、一個是兩邊都真的連不上）。這確認了 Day13.md ⑧ 節強調的重點：只看 `status` 欄位無法分辨「因為政策不准切」跟「切了但也失敗」這兩種完全不同的情況，一定要搭配 `reason` 才能還原事情經過。這也是為什麼實作 telemetry 時不能只記一個列舉值就收工。

## 發現的問題與修正

1. **ModelClient 是 Protocol，不需要直接實作**：
   文章⑦第一步定義的 `ModelClient` 用 `typing.Protocol` 表示介面合約，`PrimaryFake` 和 `FallbackFake` 無需顯式繼承就能被視為實作者。本 DIY 保持這個設計，確保可替代性。實際動手才發現的細節是：如果不小心把 `PrimaryFake.generate` 的參數名稱打錯（例如漏寫 `timeout_seconds` 的型別標註），`mypy` 或 IDE 的型別檢查完全不會報錯，因為 `Protocol` 的結構化型別檢查只認方法簽章的「形狀」，不會主動提示你少實作了什麼。這代表 Protocol 的彈性是有代價的：介面合約有沒有被正確遵守，最後還是要靠測試斷言，而不能只靠型別檢查器。

2. **`generate_with_fallback` 中的 timeout 是固定值**：
   文章例子用 `timeout_seconds=2.0`，DIY 也保持相同。實測時故意把 `PrimaryFake` 的模擬延遲調到超過這個值（讓它 `raise ModelUnavailable` 前先 `time.sleep(3)`），觀察到的行為是：整個測試案例的執行時間明顯變長，但斷言結果完全不受影響，因為 fake provider 是用「直接拋例外」模擬失敗，不是真的等到 timeout 才失敗。這點跟真實 SDK 的行為不同，真實 provider 通常要等連線真的逾時才會拋錯，這中間的等待時間本身就是需要被記錄跟優化的成本。實際應用時 timeout 應該從 request 或 configuration 傳入，Day 16 會處理 latency budget 的完整設計。

3. **只有三個測試情境**：
   文章明確列出 success、allowed fallback、denied fallback 三種路徑。其他邊界情況（如 fallback 本身失敗、重試上限、metric 記錄）超出本 DIY 範圍，屬於後續 Day 15–16 的故障演練與可觀測性擴展。跑完既有三個測試後，手動加了「兩個 provider 都失效」的臨時驗證（見上方實測結果段落），確認這個邊界情況目前會回傳 `status = unavailable`，跟「政策拒絕」共用同一個 `status` 值，只靠 `reason` 欄位的文字內容區分。這其實暴露了 `RouteOutcome` 目前設計上的一個限制：`status` 是型別安全的列舉，`reason` 卻是自由格式字串，長期維護下去容易讓不同開發者寫出用詞不一致的 `reason`，最後變成事後排查時要靠字串比對而非結構化欄位判斷發生了什麼，這點在 Day13.md 原文沒有特別提到，值得在正式導入前先決定 `reason` 是否也該收斂成一組固定的錯誤分類。

4. **沒有遠端 LLM provider**：
   文章開頭說「本文不會建立、安裝、執行或驗證你的 DIY；程式中的 provider 都是 fake provider」，DIY 保持這個設計。真實 failover 演練需要在隔離環境搭建可控故障的真實依賴（Day 15–16）。

5. **`degraded` 旗標必須一起保留**：
   文章⑦最後說「若 fallback 發生但 status 還是 `completed`，你失去了辨識降級流量的能力」，測試確認 fallback 路徑返回的 `ModelResult.degraded` 必為 `True`。動手驗證時額外試了一次「刻意把 `degraded` 欄位拿掉再跑測試」，結果 `test_allowed_task_uses_fallback` 立刻失敗在 `assert result.degraded is True` 這一行，錯誤訊息是標準的 `AttributeError: 'ModelResult' object has no attribute 'degraded'`。這個失敗訊息本身其實不夠直觀，第一次看到時容易以為是程式碼哪裡少寫了一行，要對照回文章⑦的論點才會意識到這是刻意設計的斷言，用來防止未來有人為了「讓測試先過」而偷偷刪掉這個欄位。

6. **測試檔案沒有涵蓋 `RouteOutcome` 的完整欄位比對**：
   跑完三個既有測試後，另外寫了一段互動式的 `assert` 檢查每個 `RouteOutcome` 是否同時具備 `result`、`status`、`fallback_triggered`、`reason` 四個欄位（用 `dataclasses.fields()` 檢查），確認沒有任何路徑會漏填其中一個欄位變成 `None` 卻沒被斷言到。這個檢查沒有失敗，但也讓人意識到：三個既有測試各自只斷言了自己關心的欄位子集，沒有一個測試同時檢查全部四個欄位，未來如果有人不小心在某條路徑漏填了 `reason`，現有測試不一定抓得到，這是後續要補的測試覆蓋缺口。

## 驗收

- [x] 實作完成：`app/models.py`、`app/providers.py`、`app/router.py` 包含文章⑦ 全部程式碼片段
- [x] 測試通過：三個預期情境（success、allowed fallback、denied fallback）都通過斷言
- [x] 觀測一致：實測結果與 Day13.md 表格完全對應
- [x] 無外部依賴：可在隔離環境快速驗證決策邏輯
- [x] 無真實 credential：`.env.example` 空或不存在，不會洩漏 API key

## 實作邊界

**已驗證**：
- failover decision 邏輯正確性（允許列表、例外分類）
- `RouteOutcome` 的四個欄位（result、status、fallback_triggered、reason）符合觀測合約
- 三個測試情境的路徑覆蓋

**未驗證**（超出本 DIY）：
- 真實 LLM provider 的實際行為（SDK 版本、rate limit、序列化差異）
- retry 邏輯與 jitter（Day 13.md ⑨ 提到的 bounded attempt、deadline、jitter）
- health check 訊號的可信度（Day 13.md ⑨ 切換前檢查清單）
- 回切（rollback）規則與安全驗證（Day 13.md ⑨ 切換後問題）
- 完整的 telemetry contract（metrics cardinality、log 屏蔽、trace 屬性），見 Day 13.md ⑧

根據 Day13.md 說法「若你只完成 fake provider 的單元測試，能誠實宣稱的是『router 對已列情境的決策符合測試預期』」，本 DIY 正是這個層級。

---

**下一步**（Day 15–16）：
- 在隔離環境用可控故障驗證真實 failover 行為
- 建立 chaos experiment 量化切換延遲、成功率、品質損失
- 補完 retry strategy、health check、rollback 的執行測試
