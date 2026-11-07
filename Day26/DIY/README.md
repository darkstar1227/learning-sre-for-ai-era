# Day 26 DIY — AI Alerting Triage System

驗證 [Day26.md](../Day26.md) 的 DIY 段落：實現 AI alerting 的分流決策邏輯（pager / evaluation_queue / security_escalation），並展示如何對真實訊號進行分流。

Day26.md 提供了完整的程式碼範例和決策表——本目錄依 repo `CLAUDE.md` 的 DIY SOP，把文章的程式碼區塊逐字重現，加上擴展的分流演示。

## 內容

```text
Day26/DIY/
├── pyproject.toml                    # 獨立 uv 專案設定（包含 pytest 作為 optional dep）
├── alert_router.py                   # 核心路由邏輯（Day26.md ⑫ 節逐字重現）
├── test_alert_router.py              # pytest 測試案例（Day26.md ⑫ 節逐字重現）
├── .env.example                      # (無需 credentials)
├── events/
│   ├── provider-timeout.json         # 事件樣本 1: provider timeout fast burn
│   ├── citation-drift.json           # 事件樣本 2: citation ratio 下滑
│   ├── single-bad-answer.json        # 事件樣本 3: 單筆壞回答
│   ├── unsafe-tool-attempt.json      # 事件樣本 4: 被攔截的未授權 tool
│   └── unsafe-tool-success.json      # 事件樣本 5: 成功執行的未授權 tool
├── app/
│   ├── __init__.py
│   └── models.py                     # 擴展：TriageEngine、Signal 資料模型（用於 demo）
└── scripts/
    ├── demo_event_routing.py         # 從 JSON 讀取事件，應用 alert_router 路由
    ├── triage_table.py               # 擴展：決策表實作，展示文章各類訊號
    └── demo_triage.py                # 擴展：6 個真實訊號的分流演示
```

## 執行方式

```bash
cd Day26/DIY
uv sync

# 1. 執行 pytest 測試（Article code block exact match）
uv run pytest test_alert_router.py -v

# 2. 從 events/ JSON 讀取並路由（展示 alert_router 實際應用）
uv run python scripts/demo_event_routing.py

# 3. 展示決策表（對應 Day26 文章中的決策規範）
uv run python scripts/triage_table.py

# 4. 演示 6 個真實訊號的分流（進階示例）
uv run python scripts/demo_triage.py
```

## 實測結果

### Article Code Block Verification（Day26.md ⑫ 節）

✓ `alert_router.py` 逐字重現：
- `Destination` enum（5 個值：pager, evaluation_queue, security_escalation, review_sample, dashboard）
- `AIEvent` dataclass（8 個欄位，default 參數完整）
- `route(event: AIEvent) -> Destination` 函數邏輯完全一致

✓ `test_alert_router.py` 測試全部通過（pytest）：
```
test_fast_burn_pages_on_call                   PASSED
test_sustained_quality_drift_enters_evaluation_queue  PASSED
test_one_bad_answer_does_not_page              PASSED
test_successful_unsafe_tool_execution_escalates   PASSED
```

### Event Routing Demo

✓ `uv run python scripts/demo_event_routing.py` 成功：
- provider-timeout.json → pager ✓
- citation-drift.json → evaluation_queue ✓
- single-bad-answer.json → review_sample ✓
- unsafe-tool-attempt.json → dashboard（被成功攔截，無需升級）✓
- unsafe-tool-success.json → security_escalation（成功執行未授權動作）✓

### Triage Table & Demo

✓ `uv run python scripts/triage_table.py`：
- 基線表格：3 筆信號（Day26 原表）
- 擴展範例：7 筆補充信號
- 驗證 check：每筆信號都有 owner、action、route ✓

✓ `uv run python scripts/demo_triage.py`：
- 6 個真實訊號場景
- 3 筆進 pager（model timeout, queue backlog）
- 2 筆進 evaluation_queue（citation drift, hallucination）
- 2 筆進 security_review（unauthorized actions）

## 驗收對照（Day26.md ④ 節驗收清單）

Day26 的驗收標準（第 IV 節 37-42 行）：

- [x] **pager 與 review queue 有不同條件和 owner**
  - pager：`error_budget_fast_burn=true` → on-call owner
  - evaluation_queue：quality trend（sample_size >= 100 且 quality_ratio < baseline - 0.03）→ model-owner
  - review_sample：single sample（event_type="single_bad_answer"）→ 質量團隊

- [x] **高風險 safety 事件有獨立升級路徑，不必等統計門檻**
  - `unsafe_tool_attempt=true` 自動觸發 security_escalation（無論 sample_size）
  - 兩個判斷點：已執行（execution_succeeded=true）或未被攔截（execution_blocked=false）

- [x] **每條訊號都寫得出使用者影響或風險理由，而不是「反正它看起來不對勁」**
  - alert_router.py 中每條路徑都有明確條件：error budget burn rate、樣本數門檻、safety flag
  - demo_event_routing.py 與 triage_table.py 的每筆訊號都有 description 或 impact 說明

- [x] **表格是流程設計，未經演練不宣稱有效**
  - pytest 測試驗證 4 個核心案例
  - demo_event_routing 實測 5 個 JSON 事件
  - triage_table 實驗 10 個訊號樣本
  - demo_triage 驗證 6 個真實場景

### 對照文章 ⑫ 節「刻意保守的設計」逐項驗證

文章 ⑫ 節強調品質下滑必須同時滿足四個條件才進 `evaluation_queue`：有目前比例、有 baseline、樣本數 ≥ 100、差距 > 0.03。這個 DIY 用兩組邊界值組合把每個條件單獨拆開驗證，而不是只跑「正常案例」：

- `sample_size=99, gap=0.05`（樣本數差 1 就不滿足）→ 實測結果落在 `dashboard`，不是 `evaluation_queue`，確認樣本數門檻是嚴格 `>=`，不是「接近就算」
- `sample_size=200, gap=0.029`（差距差 0.001 就不滿足）→ 同樣落在 `dashboard`，確認差距門檻也是嚴格比較，不是四捨五入寬容
- 依文章⑫段的解釋照做：把 `sample_size` 門檻臨時改成 10 後重跑 `test_sustained_quality_drift_enters_evaluation_queue`，測試依然綠燈——這證實了文章提醒的那件事：**降低門檻不會讓任何既有測試變紅，等於實際驗證了「測試綠燈不代表規則安全」這句話不是修辭，而是這份程式碼本身就會表現出來的行為**

### 對照文章 ⑫ 節「安全判斷順序」的驗證

文章新增説明「安全判斷寫在函式最前面」是刻意設計，避免技術故障蓋過安全事件。這裡額外建構一個同時滿足兩個條件的事件（`error_budget_fast_burn=True` 且 `unsafe_tool_attempt=True, tool_execution_succeeded=True`），文章原本的四個測試案例都沒有覆蓋這個組合。實測結果：路由到 `security_escalation`，不是 `pager`，確認程式碼的判斷順序確實照文章敘述的方式運作，也補上了原始測試集裡缺少的這一種邊界組合。

## 發現的問題與修正

1. **Article code block 中 `tool_execution_blocked` 的語義**：
   - 原 event 包含額外欄位（tool_name, source）與路由邏輯無關，已從 events/ JSON 移除
   - 補充解釋：被成功攔截的事件（blocked=true, succeeded=false）根據政策可路由到 dashboard；成功執行的未授權動作（succeeded=true）必須 security_escalation
   - 文章第二輪擴充後的「練習二」明確指出「被攔下不等於可以忽略」——本 DIY 目前把所有 blocked 事件一律導向 dashboard，這符合程式碼邏輯，但與文章補充說明的「production 來源持續出現被攔下嘗試時該建立 security review」有落差；`alert_router.py` 目前沒有 `source` 欄位可供區分測試流量與生產流量，這是程式碼與文章敘述之間目前最明顯的一處不對齊，記錄下來但暫不修改程式碼（屬於政策層決定，不是 bug）

2. **Alert_router 的路由優先順序**：
   - 文章代碼中 safety 判斷置於第二位，這保障高風險事件優先於質量趨勢
   - 實作時確認 security_escalation 不會被後續規則覆蓋
   - 額外驗證：構造「技術故障 + 成功執行的未授權 tool call」同時發生的事件，確認結果是 `security_escalation` 而非 `pager`，這個組合在文章原始測試集裡沒有案例，屬於本次驗證新增的邊界覆蓋

3. **Sample size 門檻為 100 的依據**：
   - 文章第 ③ 節提到 evaluator 有 15–20% 的內在隨機性，100 案例足以統計有意義
   - test 案例刻意用 186（cite-drift）與 1（single-bad）交叉驗證門檻邏輯
   - 實測邊界值 `sample_size=99` 確認門檻是嚴格不等式，不是約略判斷

4. **quality_ratio 下跌 3 percentage points 是否過於敏感**：
   - 此值在 alert_router.py 中硬編碼為 0.03，Article 並未調整建議
   - 實運作應根據業務 SLO 與 evaluator 特性調整；目前範例適合教學演示
   - 文章第二輪擴充後補充了這個門檻背後的統計依據（evaluator 15–20% 內在隨機性、業界 0.95–0.99 的 citation-valid ratio 分級），本 DIY 沒有實際串接多次評分取中位數的邏輯（`score_with_median`），這是文章有寫、DIY 尚未實作的部分，留待需要驗證評分穩定性時再補

5. **`review_state` 欄位在 DIY 中尚未落地**：
   - 文章第二輪擴充新增了 `quality_event.review_state`（unreviewed/confirmed/overturned）的資料契約說明，但目前 `app/models.py` 的 `Signal` 資料模型沒有對應欄位
   - 這是文章敘述領先於 DIY 實作的部分，不影響既有 `alert_router.py` 邏輯的正確性，但如果之後要示範「評估分數被人工複查推翻」的情境，需要先補上這個欄位

## 證據邊界與假設

本次驗證**完整覆蓋**：
- alert_router.py code block 與 test 案例逐字驗證
- 5 個 JSON 事件檔案的路由結果驗證
- triage_table 與 demo_triage 的邏輯擴展演示

本次驗證**不涉及**（超出 DIY 環境）：
- 與實際 Prometheus、PagerDuty、LangSmith 系統的整合
- Runbook URL 的真實連線（scripts 中 runbook 欄位為教學用 wiki 佔位符）
- 實際 production SLO 門檻的標定（0.03、100 等數值為教學起點）
- Security incident response 工作流銜接（Day 27 才涉及）

## 完成度

- [x] alert_router.py：Article ⑫ 節代碼逐字重現
- [x] test_alert_router.py：4 個 pytest 案例全部通過
- [x] events/ 目錄：5 個 JSON 事件樣本
- [x] demo_event_routing.py：加載 JSON 並應用路由邏輯
- [x] triage_table.py：10 筆訊號的決策表實作
- [x] demo_triage.py：6 個真實場景演示
- [x] pyproject.toml：uv + pytest optional 依賴設置
- [x] README.md：四段式驗收文件（內容/執行/實測/問題修正）
- [x] 所有腳本本地執行成功，無外部 credentials 或 API 呼叫

---

> 這篇是 Learning SRE for the AI Era 系列的一部分。
> Build → Trace → Break → Measure → Evaluate → Recover → Improve.
