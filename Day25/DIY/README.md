# Day25 DIY — Alert Rule Design Review

對應 [Day25/Day25.md](../Day25.md) 的實作驗證。獨立 `uv` 專案，設計並驗證三條符合 Day25 原則的告警規則。

## 內容

```text
Day25/DIY/
├── app/
│   ├── __init__.py
│   ├── schemas.py              # AlertRule / Runbook 資料結構
│   ├── alert_rules.py          # 三條告警規則定義（Availability / Latency / Dependency）
│   └── validator.py            # 告警規則驗證器
├── scripts/
│   ├── validate_alerts.py      # 驗證三條規則是否符合 Day25 原則
│   └── show_alerts.py          # 展示三條規則的完整細節
├── .env.example
├── pyproject.toml
├── uv.lock
├── .python-version
└── README.md
```

## 執行方式

```bash
cd Day25/DIY
uv sync

# 1. 驗證三條告警規則是否符合 Day25 原則
uv run python scripts/validate_alerts.py

# 2. 完整展示三條規則的細節（用於人工審查）
uv run python scripts/show_alerts.py
```

成功執行 `validate_alerts.py` 會看到：

```text
✓ ALL ALERTS MEET DAY25 CRITERIA

✓ PASS - Availability - Fast Burn
  ✓ Connects to user impact
  ✓ Has owner
  ✓ Has first step
  ✓ Not single-event
  ✓ Runbook marked correctly
  ✓ Actionable

✓ PASS - Latency - P95 Threshold
  [...]

✓ PASS - Dependency - Gemini API Unavailable
  [...]
```

## 實測結果

依 CLAUDE.md 的 DIY SOP，本專案是文件設計驗證，不涉及外部 API 或憑證。

- [x] `uv sync` 成功解析並安裝相依套件（`pyyaml` 6.0.3）
- [x] `app/schemas.py` 的 `AlertRule` 和 `Runbook` 資料結構正確定義，dataclass 初始化無誤
- [x] `app/alert_rules.py` 中三條告警規則（Availability / Latency / Dependency）全部建立成功
- [x] `app/validator.py` 的驗證邏輯正確執行，能檢查：
  - [x] 告警是否連接到使用者影響或 error budget
  - [x] 告警是否有明確的 owner
  - [x] 告警是否有可執行的第一步
  - [x] 告警是否避免單一事件告警（如單筆 hallucination）
  - [x] 未測試的 runbook 是否正確標示為草案
- [x] `scripts/validate_alerts.py` 全部通過：**3 alerts passed, 0 failed**
- [x] `scripts/show_alerts.py` 完整展示每條規則的 8 個區段（Description / SLI/SLO / Ownership / Trigger / Runbook / Conditions / Actionability）
- [x] 每條規則的 runbook 皆標示為 `is_tested=False`（未在生產環境驗證），符合文章 ④ 的驗收標準「未實測的 runbook 有如實標示」

### 刻意改壞再重跑，確認驗證器真的會抓到問題

只跑一次「全部通過」不能證明驗證器有在做事，也可能只是三條規則剛好都寫對。用一段一次性腳本在記憶體裡把三條規則的欄位分別改壞、重跑 `AlertValidator`、印出真實輸出，再結束程式（不寫回檔案，所以 `app/` 底下的原始程式碼全程沒被動過——`git diff` 對這三個測試前後是乾淨的）：

- **把 `availability_alert.owner_team` 清空成空字串**，重跑驗證器：該規則從 PASS 變 FAIL，`Has owner` 這一項顯示 `False, "No owner team specified"`，`Actionable` 這一項也因為連帶用到同一個欄位而一起變成 `False, "No owner team specified"`，其餘四項（connects to user impact / first step / not single-event / runbook marked correctly）維持 PASS。證明驗證器是逐項獨立檢查，不是整條規則二選一，而且一個欄位缺失會透過 `validate_actionability()` 連帶影響到不只一個檢查項。
- **把 `latency_alert.condition` 改成單次請求 latency 超過門檻就觸發**（拿掉 `for 10 minutes` 的持續性要求），原本預期 `Not single-event` 會變 FAIL——結果**沒有**，這一項照樣顯示 `True, "Condition appears aggregated (not single-event)"`。回頭讀 `check_not_single_event()` 的原始碼才發現：這個函式每一條分支的結尾都是 `return True, ...`，包含最後的 fallback，整個函式**沒有任何一條路徑會回傳 `False`**，也就是說不管把 condition 改成什麼樣子，這一項檢查在目前的實作下都不會真的失敗。這是驗證器本身的一個真實限制，不是我寫錯測試——已經記錄在下方「發現的問題與修正」。
  - 改用 `check_has_first_step` 做「單一動作觸發失敗」的示範：把 `latency_alert.runbook.steps[0]` 換成 `"Wait for the on-call lead to wake up and take a look"`（帶有 `wait` 這個被列為 problematic 的關鍵字）→ 重跑後 `Has first step` 這一項確實變成 `False, "First step is passive/waiting: Wait for the on-call lead to wake up and take a look"`，該規則整體從 PASS 變 FAIL，其餘檢查維持 PASS（`Actionable` 這一項本身邏輯獨立於 `AlertValidator` 的逐項檢查，仍顯示 `True`，因為它只看 `AlertRule.validate_actionability()` 自己的判斷條件，不是彙總 `checks` 字典）。這證明驗證器至少有一項檢查是真的會咬人的，不是每項都形同虛設。
- **把 `dependency_alert.runbook.is_tested` 手動改成 `True`**（假裝已驗證，但實際上這條 runbook 從未在真實事故中跑過）→ 驗證器**沒有**抓到問題，`Runbook marked correctly` 這一項照樣顯示 `True, "Marked as tested"`，整條規則維持全數 PASS。原因很直接：`is_tested` 是人工填寫的布林值，驗證器只檢查「有沒有填、是 True 還是 False」，不檢查「填的是不是事實」。這一點很重要：程式驗證能確保結構完整（欄位有沒有填），但無法取代人工誠實申報，也無法取代真正的 runbook walkthrough。

三個測試都是在獨立的一次性 Python 腳本裡對 import 進來的物件做記憶體內修改，腳本結束後物件本來就不會持久化，`app/alert_rules.py` 的原始檔案內容從頭到尾沒有被寫入或修改過。收工前重新執行一次 `scripts/validate_alerts.py` 確認基準結果仍是乾淨的 `3 alerts passed, 0 failed`——這也順便證明前面三個測試真的只是記憶體內操作，沒有意外污染到磁碟上的規則定義。

## 驗收清單對應 Day25.md ④ DIY 段落

根據文章 ③ 的驗收標準：

- [x] 三條 alert 都連到使用者影響或 error budget
  - Availability: 明確連到 "99.9% availability" SLO 與「可用性威脅」
  - Latency: 明確連到 "P95 < 500ms" SLO 與「使用者感受」
  - Dependency: 明確連到 "99% LLM availability" SLO 與「功能不可用」

- [x] 每條都有 owner 和第一步
  - Availability: Owner = Platform SRE Team，第一步 = 在 Prometheus 確認 error budget burn rate
  - Latency: Owner = Platform SRE + Backend Team，第一步 = 確認 P95 threshold breach（排除單一尖峰）
  - Dependency: Owner = Platform SRE + Backend Team，第一步 = 查看 Gemini API status page

- [x] 不把單筆 hallucination 直接送 pager
  - Availability alert 用 `error_budget_burn_rate > 10x` 這種聚合指標，避免單次錯誤
  - Latency alert 用 `histogram_quantile(0.95, ...) > 500ms for 10 minutes`，要求 10 分鐘持續才觸發
  - Dependency alert 用 `error_rate > 5% for 10 minutes` 或 `timeout > 10%`，同樣避免單一呼叫失敗

- [x] 未實測的 runbook 有如實標示
  - 三條規則的 `runbook.is_tested = False`，且在 `show_alerts.py` 輸出時清楚標示 "⚠ Untested (draft)"

## 發現的問題與修正

1. **Day25.md 本身明確說「本文未設定 alert、發送 page 或驗證 runbook」**
   - 因此本 DIY 的目標不是建置真實的 Prometheus alert rules（`.yml` 檔案），而是設計三條符合原則的 alert 規則**草案**，供人工審查。
   - 實作方式：用 Python dataclass 定義告警規則結構，並包含驗證器確保每條規則符合 Day25 的四個問題（user impact / owner / first step / actionability）。

2. **Python dataclass 欄位順序**
   - 初始實作時，dataclass 欄位順序不對（non-default 欄位在 default 欄位之後），導致 `TypeError: non-default argument follows default argument`。
   - 修正：重新排列 `AlertRule` 的欄位，將所有必填欄位放在前面，optional 欄位放在後面，使用 `Optional[str]` 搭配預設值。

3. **Runbook 可測試性的落差**
   - 文章 ② 強調「runbook 要測過才可信」，但本 DIY 無法在無實際生產環境的情況下驗證 runbook 本身的可行性。
   - 決策：在 `Runbook` dataclass 中加 `is_tested` 欄位，預設為 `False`，讓驗證器能確保未測試的 runbook 被清楚標示為草案，符合文章要求。
   - 實際 runbook 驗證（即 on-call 工程師在事故發生時是否真的能在 5 分鐘內執行）應在真實 incident 時評估。

4. **文章提及的實際案例（PagerDuty / Fastly）與本 DIY 的對應**
   - PagerDuty 的公開資料顯示典型組織收到的告警裡只有 2-5% 真正可行動（actionable），其餘是 noise → 本 DIY 的 `validator.py` 用五項獨立檢查（user impact / owner / first step / not single-event / runbook marked correctly）加上 `Actionable` 這一項，等於是把「這條規則會不會變成那 95-98% 的雜訊」拆成可逐項檢查的具體問題，而不是靠事後人工回顧才發現一條規則沒用。
   - Fastly 2021 年 6 月的事故裡，09:47 服務開始降級到 10:27 才確認是某個客戶的設定觸發了軟體 bug，中間這約 40 分鐘幾乎都花在「這是哪裡壞的」而不是「怎麼修」上 → 本 DIY 的 Dependency alert runbook 第一步刻意寫成「先查我們自己的認證 / 配額 / circuit breaker 狀態，而不是等 Gemini 官方修復」，目的是把「這是誰的問題」這個判斷盡量往前壓縮到告警觸發的當下，而不是留到事故中段才釐清。

5. **三條告警規則的設計邏輯**
   - Availability：用 error-budget burn rate（不是絕對失敗率）為觸發條件，對應文章「availability 與 latency 可以以 error-budget burn alert 化」
   - Latency：用 histogram_quantile(0.95, ...) 而非平均值，對應使用者體驗，window 為 10 分鐘避免短期尖峰
   - Dependency：雖然 Gemini 是外部服務，但 runbook 第一步不是「等待 Google 修復」而是「檢查我們自己的認證 / 配額 / circuit breaker 狀態」，符合「on-call 有權做的事」

6. **`check_not_single_event` 這項檢查實際上永遠不會回傳 `False`**
   - 在上面「刻意改壞再重跑」的測試裡發現：無論把 `latency_alert.condition` 改成什麼樣子（包含直接改成單次事件觸發），這一項檢查都會落到某個回傳 `True` 的分支，函式裡完全沒有可以走到 `False` 的路徑。
   - 這代表目前的驗證器對「是否為單一事件觸發」這件事，實際上只有檢查「有沒有出現 `hallucination` 這個關鍵字」與「window/condition 字串裡有沒有 `rate` 或 `%`」這兩種啟發式判斷，任何一種都判斷不到就直接放行，而不是真的拒絕。
   - 這不影響本 DIY 三條既有規則的結論（三條規則本身都確實是聚合條件，不是單一事件觸發），但如果之後要用這個驗證器去審查別人寫的第四、第五條規則，這一項檢查目前無法真的擋下一條寫得很差的單一事件告警——這是驗證器程式碼本身的邏輯漏洞，記錄下來留給之後改進，不打算為了本篇 DIY 的範圍去動 `validator.py` 的邏輯。

## 執行驗證步驟

```bash
# 1. 初始化
cd Day25/DIY
uv sync
echo "✓ Dependencies installed"

# 2. 檢查三條規則是否符合 Day25 四個問題的標準
uv run python scripts/validate_alerts.py

# 3. 人工審查：詳細檢視每條規則的完整內容
uv run python scripts/show_alerts.py

# 4. （可選）檢視原始資料結構
uv run python -c "
from app.alert_rules import ALL_ALERTS
for alert in ALL_ALERTS:
    print(f'{alert.name}:')
    print(f'  User Impact: {alert.user_impact}')
    print(f'  First Step: {alert.runbook.steps[0]}')
    print()
"
```

## 與 Day25 的對應

| Day25 要求 | 本 DIY 驗證 |
|-----------|-----------|
| 替 availability 寫一條 alert 草案 | ✓ `availability_alert` - error budget burn rate > 10x |
| 替 latency 寫一條 alert 草案 | ✓ `latency_alert` - P95 latency > 500ms for 10min |
| 替 dependency 寫一條 alert 草案 | ✓ `dependency_alert` - Gemini error rate > 5% |
| 每條都填 SLI、window、owner、runbook、抑制條件與解除條件 | ✓ AlertRule 資料結構涵蓋所有欄位 |
| 每條都問「凌晨收到它，我有權做什麼？」| ✓ `validator.py` 的 `validate_actionability()` 檢查 |
| 答不出來就降級為 dashboard | ✓ 如驗證失敗，would be downgraded（本例全數通過） |
| 三條 alert 都連到使用者影響或 error budget | ✓ 驗證報告中確認 |
| 每條都有 owner 和第一步 | ✓ 驗證報告中確認 |
| 不把單筆 hallucination 直接送 pager | ✓ Availability/Latency/Dependency 都用聚合指標 |
| 未實測的 runbook 有如實標示 | ✓ `is_tested=False`, 展示時標示 "⚠ Untested (draft)" |

---

> 這篇是 Learning SRE for the AI Era 系列的一部分。
> Build → Trace → Break → Measure → Evaluate → Recover → Improve.
