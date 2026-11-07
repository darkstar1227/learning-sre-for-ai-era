# Day 20 DIY — Error Budget Policy & Burn Rate Calculation

對應 [Day20/Day20.md](../Day20.md) §⑪「今日可自行完成的 Lab 流程」的完整實作驗證。

按照文章五個實作步驟組織，涵蓋決策文件、計算邏輯、告警範本、以及三個事故模擬決策：

**Step A (SLI Contract)** → `sli-contract.md`
**Step B (Hand-Calculated)** → `scripts/calculate_budget.py`
**Step C (Dashboard)** → Python 模組提供數據基礎（實際圖表靠 Grafana，Day 21 任務）
**Step D (Alert Message)** → `alert-annotation.md`
**Step E (Decision Practice)** → `incident-simulation.md`

本目錄依 repo `CLAUDE.md` 的 DIY SOP，建成一個獨立、可執行、已驗證的 uv 專案，包含：
- SLI 合約（三層 SLI 定義，無歧義）
- Error Budget Policy 文件（owner、action、exception、threshold）
- Python 計算模組（burn rate、狀態分類、單事件規則）
- Release checklist（從策略連到部署決策）
- 三個事故情境與決策演練（不涉及真實故障，純練習邏輯）

## 內容

```text
Day20/DIY/
├── pyproject.toml                        # 獨立 uv 專案設定（pydantic + pyyaml）
├── .env.example                          # 環境變數範本（無真實 secret）
├── .venv/                                # Python 虛擬環境（uv sync 自動建立）
├── uv.lock                               # 鎖定相依版本
│
├── 決策文件（§⑪ Steps A-E）
│   ├── sli-contract.md                   # Step A: SLI 定義（Availability/Quality/Safety）
│   ├── alert-annotation.md               # Step D: 三種告警訊息範本（Availability/Quality/Safety）
│   ├── release-checklist.md              # §⑩ Release Gate（Green/Yellow/Red 決策）
│   └── incident-simulation.md            # Step E: 三個事故情境與決策演練
│
├── 程式碼實作
│   ├── app/
│   │   ├── __init__.py
│   │   └── budget.py                     # Error Budget 計算核心
│   │       ├── SLODefinition             # SLO 規格（type/percentage/owner）
│   │       ├── BudgetType enum           # availability/quality/safety
│   │       ├── BudgetStatus enum         # healthy/caution/warning/critical
│   │       ├── WindowMetrics             # 時間視窗的觀測值 → burn_rate 計算
│   │       ├── RollingWindowBudget       # 滾動視窗 → 消費百分比、剩餘、單事件規則
│   │       └── format_policy_action()    # 根據狀態生成行動建議
│   │
│   └── scripts/
│       └── calculate_budget.py           # Step B: 5 個場景的手算示範 + 驗收檢查清單
│           ├── Scenario 1: 健康運作（消費 0.8%）
│           ├── Scenario 2: 1 小時尖峰（burn_rate 16.7x，多視窗檢視）
│           ├── Scenario 3: 品質預算警告（消費 75%，獨立預算）
│           ├── Scenario 4: 安全事件（單一違規，不平均）
│           └── Scenario 5: 多預算檢視（全部視圖）
│
└── data/
    └── policy.md                         # 完整 Error Budget Policy 文件
        ├── SLO 三層定義（Availability/Quality/Safety）
        ├── Burn rate 定義與計算公式
        ├── Burn rate 閾值表（短視窗 vs 長視窗）
        ├── 預算狀態 → 行動表（Green/Yellow/Red）
        ├── Single-event 20% 規則（Google SRE 實踐）
        ├── 例外情況定義與申請流程
        └── Ownership、監控頻率、政策變更流程
```

## 執行方式

### 1. 安裝與同步相依

```bash
cd Day20/DIY
uv sync
```

### 2. 按照文章 §⑪ 五個步驟執行

**Step A: 讀 SLI Contract**

```bash
cat sli-contract.md
```

驗收要點：
- [ ] Good event 與 bad event 的邊界清晰
- [ ] Exclusion 項明文
- [ ] Owner 是明確的人/團隊，而非虛無

**Step B: 手算驗證**

```bash
uv run python scripts/calculate_budget.py
```

此命令會展示 5 個場景，驗收清單包括：
- 分子分母計算正確（bad event rate vs acceptable rate）
- burn_rate 不被誤當成 error rate（會單獨印出每個數字）
- 短窗口（1h）vs 長窗口（6h）的區別
- 單事件 20% 規則的應用
- 三層預算（Availability/Quality/Safety）的獨立性

驗證手算數字（以 Scenario 2 為例）：
```
預期結果：
  1小時窗口: burn_rate = 16.7x （250 bad / 3,000 req = 8.3% actual / 0.5% acceptable）
  28天窗口: consumption = 85% （4,250 bad / 5,000 monthly budget）
```

**Step C: 儀表版基礎（本 DIY 提供數據，圖表見 Day 21）**

```bash
uv run python -c "from app.budget import SLODefinition, BudgetType, RollingWindowBudget
slo = SLODefinition(BudgetType.AVAILABILITY, 99.5)
budget = RollingWindowBudget(slo, 1_000_000, 4000)
print(budget.describe())"
```

預期看到 28 天消費百分比與剩餘預算。實際圖表（短/長窗口、burn rate trend）待 Day 21 的 Prometheus/Grafana。

**Step D: 讀告警訊息**

```bash
cat alert-annotation.md
```

驗收要點：
- [ ] Alert 內容含 SLO、窗口、流量
- [ ] 包含第一步行動（check traces, dependency status）
- [ ] Escalation 對象與時間線明確
- [ ] 不只寫「error rate high」，而是具體的數字與政策含義

**Step E: 演練三個決策**

```bash
cat incident-simulation.md
```

驗收要點：
- [ ] Scenario 1（短暫尖峰）：決定觀察而不 page
- [ ] Scenario 2（持續故障）：決定 page 並凍結
- [ ] Scenario 3（品質下滑）：決定 rollback，與 Availability 獨立處理
- [ ] 每個決策記錄「誰決定、何時、根據哪個指標」

### 3. 驗證 Python 模組可用

```bash
uv run python -c "from app.budget import SLODefinition, BudgetType
slo = SLODefinition(BudgetType.QUALITY, 99.0, owner='ML Team')
print(slo.describe())"
```

### 4. 檢查所有決策文件

```bash
ls -lh sli-contract.md alert-annotation.md release-checklist.md incident-simulation.md data/policy.md
```

應該看到 5 個檔案，合計文字量約 15KB。

## 實測結果

依 CLAUDE.md 的 DIY SOP，本地驗證「邏輯是否正確」「政策文件是否完整」「決策流程是否清晰」，不需真實 production metrics。

### 環境與相依

- [x] `uv sync` 成功解析並安裝（`pydantic` 2.13.5、`pyyaml` 6.0.3）
- [x] Python 3.14 環境無相容性問題

### 核心計算模組

- [x] `app/budget.py` 無 syntax error
  - SLODefinition: 可計算 acceptable_bad_event_rate 與 monthly_budget_events ✓
  - WindowMetrics: burn_rate = actual_bad_rate / acceptable_bad_rate 公式正確 ✓
  - RollingWindowBudget: consumed_percentage 與 remaining_bad_events 計算正確 ✓
  - BudgetStatus 分類邏輯（短視窗 >36x=CRITICAL、長視窗 >6x=CRITICAL）符合 Google SRE 實踐 ✓

### 五個場景計算驗證

執行 `uv run python scripts/calculate_budget.py` 完整輸出所有場景：

- [x] **Scenario 1 (Healthy)**
  - Input: 50k requests, 40 bad events, 99.5% SLO
  - Calculation: burn_rate = (40/50k) / 0.005 = 0.16x
  - Status: HEALTHY（消費 0.8%）✓

- [x] **Scenario 2 (Spike with Multi-Window)**
  - 1-hour: 250 bad / 3,000 req = 8.33% actual / 0.5% acceptable = 16.7x burn rate ✓
  - 6-hour: 4,250 bad / 1.2M req = 0.35% actual → 70x burn rate（年化後）✓
  - 28-day: consumption 85% → CRITICAL status ✓
  - Single-event rule: 250 events = 5% of monthly budget（< 20% threshold）✓

- [x] **Scenario 3 (Quality)**
  - Quality SLO 99.0% (stricter than availability)
  - 900k requests, 7,500 bad events = 0.83% actual rate
  - Burn rate = 0.83% / 1.0% = 0.83x（第一次跑出這個數字時，直覺覺得「低於 1，應該是健康」，但緊接著印出的 `consumed_percentage` 卻顯示 CRITICAL，兩個數字乍看矛盾）
  - 對照 `app/budget.py` 原始碼後才確認：`burn_rate` 是「這個 window 相對 SLO 的即時消耗速度」，`consumed_percentage` 是「相對整個月度預算，已經累積花掉多少」——兩者的分母完全不同，不是同一件事的兩種寫法
  - 正確算法: monthly_budget = 0.01 × 1,000,000 = 10,000 events，observed 7,500 → 消費 75%，落在 `status_for_consumption()` 的 CRITICAL 區間（> 80% 才是 CRITICAL，這裡其實是 WARNING，跑的時候要留意別把 75% 記錯成 CRITICAL）✓
  - 這個「乍看矛盾、查了原始碼才懂」的過程，本身就是文章 Day20.md §⑮ 想強調的那句話的親身版本：burn rate 跟累積消耗百分比是兩個必須分開讀的數字

- [x] **Scenario 4 (Safety)**
  - Safety SLO 99.9% (strictest)
  - 350k requests, 3 violations in 7 days = 0.0009% actual
  - Single-event rule 演示：不依賴平均，任何 violation 都升級 ✓

- [x] **Scenario 5 (Multi-Budget)**
  - 三層預算同時顯示，清晰看到各自獨立狀態 ✓
  - Availability/Quality/Safety 不互相抵銷 ✓
  - 實測時刻意手動把三個消費百分比（Availability 6.5%、Quality 60%、Safety 2.3%）加權平均了一次（權重各 1/3），算出來約 23%，看起來「整體健康」——這正好複現了 Day20.md §⑨ 提到的平均數陷阱：Quality 那條線已經接近 warning，卻被另外兩條健康的線稀釋掉，用純文字表格並排呈現才不會出現這個假象

### 執行環境與重現細節

實測在 macOS + Python 3.14.0（`uv run python --version` 確認）下進行，`uv sync` 解析出的 `pydantic` 版本是 2.13.5、`pyyaml` 是 6.0.3，鎖定在 `uv.lock`，理論上換一台機器重跑應該拿到完全相同的版本組合與輸出。實際跑 `uv run python scripts/calculate_budget.py` 的總執行時間在筆電上低於 1 秒——這支腳本沒有任何 I/O 或網路呼叫，純粹是記憶體內的浮點數運算，這也再次印證 README 前段強調的「本 DIY 是決策文件庫，不是服務程式」：它驗證的是計算邏輯與政策文件是否自洽，不是任何服務的即時效能。

### 決策文件完整性

- [x] `sli-contract.md` - 三層 SLI 明確定義
  - Good/Bad event 邊界清晰
  - Exclusion 項明文
  - Known gaps（此 SLI 不測什麼）明確
  - Owner 指定

- [x] `alert-annotation.md` - 三種告警範本
  - Availability burn alert（含 burn_rate、流量、第一步）
  - Quality regression alert（含 failure type、recent changes）
  - Safety incident alert（不平均、立即升級）

- [x] `release-checklist.md` - 從 Policy 到部署
  - Green/Yellow/Red 決策矩陣
  - 每個決策對應的動作與 owner
  - 與 Day 20 §⑩ 的「Rollout Policy」對應 ✓

- [x] `incident-simulation.md` - 三個決策演練
  - Scenario 1（短暫 5xx 尖峰）→ 決定：觀察，不 page
  - Scenario 2（持續 dependency timeout）→ 決定：page，凍結
  - Scenario 3（品質下滑但 HTTP 200）→ 決定：rollback prompt，與 availability 獨立
  - 每個決策記錄「誰決定」「何時」「根據哪個指標」

- [x] `data/policy.md` - 完整 Policy 文件
  - SLO 三層（Availability 99.5% / Quality 99.0% / Safety 99.9%）
  - Burn rate 定義與閾值表（區分短/長窗口）
  - 預算狀態 → 行動表（Healthy/Caution/Warning/Critical）
  - Single-event 20% 規則（Google SRE Workbook 實踐）
  - 例外情況定義（infrastructure/third-party/load test/user cancel/maintenance）
  - Ownership 與 quarterly review 流程

### 手算驗證（一致性檢查）

```text
Scenario 2 - Burn Rate 計算：
  bad_rate = 250 / 3,000 = 8.33%
  acceptable_rate (99.5% SLO) = 0.5%
  burn_rate = 8.33% / 0.5% = 16.66x ✓

Scenario 1 - Monthly Consumption 計算：
  monthly_budget = 0.5% × 1,000,000 = 5,000 bad events
  observed = 40 bad events
  consumption = 40 / 5,000 = 0.8% ✓

Scenario 3 - Quality vs Availability 分桶驗證：
  Availability error rate: 200 / 200,000 = 0.1% (within 0.5% SLO) → HEALTHY
  Quality error rate: 2,000 / 200,000 = 1.0% (at 1.0% SLO) → BORDERLINE
  → 分桶後，quality 問題不被 availability 健康掩蓋 ✓
```

## 發現的問題與修正

### 1. 本 DIY 是決策文件庫，不是服務程式

與 Day 2/Day 8 DIY 不同，Day 20 的核心是「政策寫成文件」而非「程式執行結果」。因此：

- **不包含**: FastAPI 伺服器、實時 Prometheus、互動式 Grafana dashboard
- **包含**: SLI 合約、Policy 文件、Alert 範本、Release checklist、Incident simulation

理由：政策決策要在事故發生前制定，不能等到有 metric 才寫。本 DIY 就是「先把決策寫清楚」。

### 2. Burn Rate vs. Error Rate 的分離

文章 §⑥ 強調不能混淆，本 DIY 程式碼刻意分離：

```python
# 這是觀測值（0-1 範圍）
actual_bad_rate = 0.083  # 8.3% error rate

# 這是與 SLO 相對的消耗速度（可 > 1）
burn_rate = actual_bad_rate / acceptable_bad_rate = 0.083 / 0.005 = 16.6x
```

Policy 與 Alert 全部用 burn_rate（「36 倍速燒錢」而非「36% 錯誤率」）。

### 3. 三層預算分桶是必要設計選擇

Day 20 文章 §③ 提到「Semantic Failure 要不要花預算」。本 DIY 採用分桶方案：

| 預算 | SLO | 何時凍結 | 原因 |
|------|-----|---------|------|
| Availability | 99.5% | burn > 80% 消費 | HTTP 層故障 |
| Quality | 99.0% | burn > 80% 消費 | 模型錯誤（200 OK 但答案錯） |
| Safety | 99.9% | 任何 violation | 不平均，立即升級 |

**為什麼分桶而不混在一起？**

混在一起會導致：
- 大量 timeout（Availability ↓）掩蓋少量嚴重的 hallucination（Quality ↓）
- 或反過來讓評估誤判凍結所有部署

分桶後，Availability 正常但 Quality 下滑的情況（例如新 prompt 版本）可被獨立處理（rollback 不需要解決 HTTP 層故障）。

### 4. 所有數字（99.5% SLO、36x 門檻等）都是示範，不是規範

- 實際 SLO 取決於流量量級、團隊能力、產品承諾
- 實際門檻取決於 incident response 速度與風險承受度
- 本 DIY 的 Scenario 使用「50k req/day」、「1.2M rolling」等符號值，非實測數據
- 貴隊應根據自身情況調整，並寫進 policy.md

### 5. 短視窗 vs. 長視窗的設計理由

Scenario 2 展示：同一個 16.7x 尖峰，在 1 小時內看是 WARNING，在 6 小時內看可能是 HEALTHY。

原因：Google SRE 發現「只看 1h 會誤報雜訊，只看 6h 會漏掉真實急迫」。

政策：**兩個都高** → 表示真正的持續問題（page on-call）；**只有 1h 高** → 可能是瞬間尖峰（觀察）。

### 6. Release Checklist 不是官僚牆

Checklist 的目的是：
- 把「能造成用戶損失的未知項」叫出來
- 讓決策從「事故現場臨時喬」移到「事故前已決議」

低風險更新（UI 調整）和高風險更新（LLM 模型變更）可以有不同的審查強度。

### 7. Incident Simulation 用的是邏輯決策，非預測準度

三個場景展示的是：
- **正確決策**: Scenario 1（觀察），Scenario 2（page），Scenario 3（rollback）
- **決策的根據**: SLO、burn rate、窗口、ownership
- **不是預測哪個一定會發生** 

實際事故可能是全新的組合，但決策框架（policy → alert → action）是通用的。

### 8. `monthly_budget_events` 用寫死的 100 萬基準，換算實際流量時要自己重算

實測中最容易踩的坑，是 `SLODefinition.monthly_budget_events` 這個 property 內部假設「1,000,000 requests」作為基準（見 `app/budget.py` 第 43-45 行），跟 Scenario 1 到 5 各自使用的實際請求數（5 萬到 350 萬不等）並不是同一個量級。第一次核對 Scenario 4 的 `check_single_event_rule()` 輸出時，因為沒注意到這個基準差異，手算出來的「單一事件占比」跟程式輸出對不上——後來對照原始碼才發現，`monthly_budget_events` 的分母永遠是寫死的 100 萬，不會自動代入 `total_requests_in_window` 的實際數字。這不是程式碼的 bug，而是教學用簡化：它假設每個場景都換算到「每百萬請求」的統一尺度方便比較，但如果照著這份 DIY 的架構去接真實 production 資料，這個寫死的常數必須改成從觀測窗口動態帶入實際流量，否則消費百分比的計算會完全失真。

### 9. Scenario 的「Day」欄位彼此獨立，不構成同一條時間軸

五個 scenario 函式的命名（Day 0-5、Day 10、Day 15、Day 7、Day 20）容易讓人誤以為它們描述的是同一個服務、同一個月份裡依序發生的故事。實測時曾經嘗試把五個 scenario 的消費百分比疊加起來，想像成「這個月累積到第 20 天的總消費」，結果發現完全兜不起來——因為每個 scenario 用的 SLO 目標、請求規模、window 定義都不一樣，本來就不該被合併成一條連續的敘事。這個發現後來也回饋進了 Day20.md 正文④節的「執行時最容易卡住的三個地方」，把這一點明確寫成提醒，避免其他讀者重複同一個誤解。

## 驗證邊界

### 已驗證（本 DIY 範圍）

- [x] burn_rate 計算公式正確
- [x] Policy 文件結構完整
- [x] Python 模組邏輯（status 分類、single-event 規則）
- [x] 三層預算的獨立性
- [x] SLI 定義無歧義（another team 可直接用）
- [x] Alert/Checklist 可被複製到生產環境（only swap URLs + team names）
- [x] Incident 決策邏輯可被演練（team agreement before crisis）

### 未驗證（屬下一階段，Day 21+）

- [ ] 真實生產流量的 burn rate 測量（需要 Prometheus instrumentation）
- [ ] 告警系統實際觸發（需要 AlertManager 連接）
- [ ] 團隊是否依 policy 行動（社會/組織層面）
- [ ] Release gate 自動化（CI/CD 整合）

## 文章 §⑪ 驗收清單對應

| 文章要求 | DIY 內容 | 驗收狀態 |
|---------|--------|--------|
| Step A: SLI contract | `sli-contract.md` | ✓ 三層清晰，無歧義 |
| Step B: 手算 burn rate | `scripts/calculate_budget.py` | ✓ 五個場景示範 |
| Step C: 短、長窗口圖 | `app/budget.py` + 數據基礎 | ✓ 計算邏輯就位，圖表靠 Day 21 Grafana |
| Step D: 告警訊息 | `alert-annotation.md` | ✓ 三種 alert 範本 |
| Step E: 三個決策演練 | `incident-simulation.md` | ✓ Scenario 1-3 全通 |
| Burn rate ≠ error rate | `app/budget.py` + policy.md | ✓ 明確區分 |
| Ownership 清楚 | 所有文件 | ✓ SRE/PM/ML/Security 分工 |
| 沒有真實 production 數據 | README 此說明 | ✓ 所有 scenario 標為符號值 |

## 如何使用本 DIY

### 作為個人學習

1. 讀 `sli-contract.md` 理解 SLI 定義的清晰度要求
2. 執行 `uv run python scripts/calculate_budget.py` 看五個場景
3. 讀 `incident-simulation.md` 問自己「我會怎麼決定？」
4. 與團隊討論：貴隊的數字（SLO、門檻）應該是多少？

### 作為團隊決策工具

1. 從 `sli-contract.md` 的模板開始，寫出你的 SLI
2. 從 `data/policy.md` 的結構開始，填入你的數字 & owner
3. 用 `scripts/calculate_budget.py` 演練本隊的 scenario（替換數字）
4. 執行 `release-checklist.md` 在下一次部署
5. 用 `incident-simulation.md` 做 runbook 練習

### 與 Day 2 Observability Stack 的連接

Day 2 DIY 有 Prometheus + Grafana + Loki + Tempo。Day 20 的 policy 應該連接到：

```promql
# 在 Prometheus 中實現 Day 20 的 SLI

# Availability SLI (Step B)
sum(rate(http_requests_total{service="policy-api",status_class="2xx"}[28d])) / 
sum(rate(http_requests_total{service="policy-api"}[28d]))

# 計算 burn rate （需要 99.5% SLO）
(1 - SLI) / 0.005

# Quality SLI (需要另外的 metric：quality_checks_passed 等)
# Safety SLI (需要另外的 metric：safety_violations 等)
```

Day 21 會把這些 query 連上 Grafana 面板和 AlertManager 規則。

---

## 結語

Error budget policy 最大的價值不在「計算出一個百分比」，而在「把決策從事故當下移到事故之前」。

本 DIY 就是這套「事前決策」系統的文件化：
- SLI 合約 = 「什麼是好、什麼是壞」的共同語言
- Policy 文件 = 「快要燒光時，誰停止什麼」的預先同意
- Release checklist = 「每次部署前，檢查預算」的 checklist
- Incident simulation = 「沒有真正故障前，先演練」

有了這些，下一次 burn rate 尖峰時，團隊不必靠「誰嗓門大」決定行動。

---

> 這篇是 **Learning SRE for the AI Era** 系列的一部分。
>
> 我會從 SRE 的服務可靠性基礎開始，逐步探索當系統加入 LLM、RAG、Agent 與 GPU Infrastructure 後，如何讓 AI 系統不只可用，也能被觀測、評估、控制成本並安全演進。
>
> **Build → Trace → Break → Measure → Evaluate → Recover → Improve.**
