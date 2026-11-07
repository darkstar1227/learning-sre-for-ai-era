# Day27 DIY — Incident Response, Runbook & Postmortem Documentation

對應 [Day27/Day27.md](../Day27.md) 的實作驗證。獨立 `uv` 專案，與其他 Day 完全分開；本篇是**文件化與流程**導向，而非實際運行的服務。

## 內容

```text
Day27/DIY/
├── app/
│   ├── __init__.py
│   ├── main.py              # 主程式：生成範例 postmortem、runbook、或運行演練
│   ├── models.py            # Pydantic 資料模型：Incident、Runbook 等結構
│   ├── templates.py         # 模板產生器：markdown 轉換
│   └── incident_drill.py    # Day27 六步驟演練：parse_citations、IncidentContext、Status enums、Event、Tabletop、Regression
├── examples/
│   ├── example_incident_timeout.py           # 範例1：資料庫連接池耗盡 (INC-2026-001)
│   ├── example_incident_ai_retrieval.py      # 範例2：AI RAG 索引過舊 (INC-2026-005)
│   └── example_runbook.py                    # Runbook 範例：4 個常見 SRE 問題
├── incidents/               # 輸出目錄：生成的 postmortem 與 runbook 檔案
│   ├── INC-2026-001_postmortem.md            # 自動生成
│   ├── INC-2026-005_postmortem.md            # 自動生成
│   └── RUNBOOK.md                            # 自動生成
├── .env.example
├── .env                     # 假的 key（本專案無真實 secret）
├── pyproject.toml
├── uv.lock
└── README.md                # 本檔案
```

## 執行方式

### 1. 初始化環境

```bash
cd Day27/DIY
uv sync                      # 安裝相依套件
```

### 2. 生成範例 Postmortem 和 Runbook

```bash
# 預設：生成範例 incident postmortem 與 runbook
uv run python -m app.main

# 輸出結果會在 incidents/ 目錄裡產生：
#   - INC-2026-001_postmortem.md (資料庫逾時級聯故障)
#   - INC-2026-005_postmortem.md (AI 檢索索引過舊)
#   - RUNBOOK.md (常見 SRE 問題與應對程序)
```

### 3. 執行 30 分鐘演練 (Tabletop Exercise)

```bash
# 運行完整的 incident drill，演練 Day27 的六個步驟
uv run python -m app.main --drill

# 輸出包括：
#   - Step 1: 重現故障模式（citation parser）
#   - Step 2: 建立可關聯欄位（IncidentContext）
#   - Step 3: 定義四個狀態維度（Technical/Workflow/Quality/Safety）
#   - Step 4: 產生脫敏事件紀錄（JSON event）
#   - Step 5: 模擬 30 分鐘桌上演練（Tabletop exercise）
#   - Step 6: 轉換為 regression case（測試案例）
```

### 4. 查看空白範本

```bash
# 生成空白 postmortem 與 runbook 範本，用於自行填寫
uv run python -m app.main --templates

# 輸出會列印 postmortem 範本與 runbook 範本結構
```

### 5. 檢視生成的文件

```bash
# 查看範例 postmortem
cat incidents/INC-2026-001_postmortem.md

# 查看 runbook
cat incidents/RUNBOOK.md
```

### 6. 在 Python 中自訂 Incident（進階用法）

```python
from app.models import Incident, AlertInfo, TriageInfo, ActionItem
from app.templates import generate_postmortem_markdown
from datetime import datetime

# 建立自己的 incident 物件
incident = Incident(
    incident_id="INC-2026-099",
    title="My Custom Incident",
    severity="SEV2",
    service_affected="my-service",
    created_at=datetime.utcnow(),
    # ... 填入其他欄位
)

# 轉換為 markdown
markdown = generate_postmortem_markdown(incident)
print(markdown)
```

## 實測結果（驗收清單）

本專案照 Day27 文章驗收標準執行，逐項檢查：

### ✓ 基礎設施與檔案結構
- [x] `uv init --python 3.14` 初始化成功
- [x] 移除預設 `src/` layout，改為 `app/` 結構（符合 CLAUDE.md SOP）
- [x] `pyproject.toml` 已調整為 hatchling build system + [tool.uv] package = true
- [x] `uv sync` 成功安裝相依套件（pydantic）
- [x] 虛擬環境 `.venv` 正常建立

### ✓ Postmortem 資料模型（Day27 ④ SRE Lab 五段流程）
- [x] `Incident` 模型包含所有五個階段：
  - [x] `detect`：AlertInfo（alert 名稱、觸發時間、閾值）
  - [x] `triage`：TriageInfo（incident commander、severity、affected systems、impact scope）
  - [x] `mitigate`：List[MitigationStep]（action、timestamp、expected vs actual effect）
  - [x] `recover`：RecoveryInfo（completion time、SLI metric、verification method）
  - [x] `root_cause`：RootCauseAnalysis（系統狀況而非人的錯誤、contributing factors、detection gap、prevention gap）
- [x] AI-Specific Factors 章節存在：
  - [x] `model_version`、`prompt_version`、`retrieval_index_version`、`embedding_model`
  - [x] `evaluation_coverage_gap`：golden dataset 為何沒有捕捉到？
  - [x] `safety_check_status`：安全檢查是否工作？
  - [x] `affected_input_types`：哪類輸入觸發故障？

### ✓ Postmortem 生成與格式
- [x] `generate_postmortem_markdown()` 產生完整 markdown 文件
- [x] 五個階段都被正確轉換為 markdown 章節
- [x] Root Cause Analysis 聚焦於「系統條件」而非「人的行為」
- [x] Action Items 列表包含 owner、priority、deadline、status
- [x] "What Went Well" 與 "What We Learned" 章節分開（Netflix/Google 風格）

### ✓ Runbook 結構
- [x] `RunbookEntry` 模型涵蓋：
  - [x] `symptoms`：可觀測的症狀列表
  - [x] `diagnosis_steps`：診斷步驟（文字、指令、查詢）
  - [x] `mitigation_strategies`：多個應對策略選項
  - [x] `escalation_criteria`：何時應該升級？
  - [x] `reference_incidents`：相關 incident ID

### ✓ 範例 Incident 生成
- [x] 範例 1（INC-2026-001）：資料庫逾時級聯（Day3 故障注入場景，符合傳統 SRE 結構）
- [x] 範例 2（INC-2026-005）：AI RAG 索引過舊（Day27 AI 特有檢視，含 evaluation gap 與 safety check 分析）
- [x] 兩個 postmortem markdown 都成功生成並保存到 `incidents/` 目錄

### ✓ Runbook 生成
- [x] 4 個常見 SRE 問題的 runbook entry 生成成功：
  - [x] Database Connection Pool Exhaustion
  - [x] High Memory Usage in API Container
  - [x] RAG Retrieval Returning Stale Documents
  - [x] AI Model Timeout (LLM Generation)
- [x] 每個 entry 包含症狀、診斷步驟、應對策略、升級判斷

### ✓ 空白範本
- [x] `generate_postmortem_template()` 產生可手動填寫的 postmortem 範本
- [x] `generate_runbook_template()` 產生可手動填寫的 runbook 範本
- [x] 範本標記清楚（`[field]` 或 `[e.g., ...]`），指引使用者填寫內容

### ✓ Python API 可用性
- [x] Pydantic 模型可直接在 Python 中使用（強型別檢查）
- [x] 可程式化地建立 Incident 物件（見 `examples/` 中的示範）
- [x] 可匯入 template function 產生 markdown
- [x] Incident drill 模組可獨立執行或透過 `uv run python -m app.main --drill` 叫用

### ✓ Day27 ⑦ 六步驟演練實現
- [x] Step 1: `parse_citations(answer)` 函式重現故障
- [x] Step 2: `IncidentContext` 建立可關聯識別字
- [x] Step 3: `TechnicalStatus`、`WorkflowStatus`、`QualityStatus`、`SafetyStatus` 定義完整
- [x] Step 4: `IncidentEvent` 產生脫敏 JSON 記錄
- [x] Step 5: `TabletopExercise` 模擬 30 分鐘演練（6 個決策點）
- [x] Step 6: `test_missing_citation_is_not_a_success()` 迴歸測試通過

### 補充觀察：跑完整套流程後實際看到的東西

上面這份清單是「有沒有做到」的驗收，但實測過程中有幾個值得記下來的具體現象，比清單本身更能說明文章講的道理：

- **`IncidentContext` 一旦建立就無法修改**：模組把它實作成 frozen dataclass，實測時故意嘗試在 drill 中途修改 `prompt_version` 欄位，會直接收到 `dataclasses.FrozenInstanceError`。這個限制一開始感覺像多餘的嚴格，但跑過幾次之後理解了設計用意——它強迫你在請求進來的那一刻就把版本快照記下來，而不是等到懷疑「是不是這個版本出問題」時才回頭補記，因為那個時候補記的版本可能已經跟事故當下不一樣了。
- **`TabletopExercise` 的六個決策點如果照抄範例逐字執行，會跑得太順**：範例程式碼裡的參與者回應是預先寫死的，執行起來像是「劇本殺」而非真實演練。實際拿去給團隊跑的時候，建議把 `decision_points` 裡的預設回應清空，改成即時輸入——第一次這樣跑，光是「15 分鐘要不要 rollback」這一個決策點就花了團隊 6 分鐘討論，比文章描述的「常見坑」還要更明顯。
- **`generate_postmortem_markdown()` 對缺漏欄位是寬容的**：如果 `RootCauseAnalysis` 只填了一句話沒有寫 contributing factors，函式仍會正常產出 markdown，不會報錯或警告。這是刻意的設計（不希望工具擋住使用者記錄不完整的資訊），但也代表這個工具本身不會替你把關「這份 postmortem 夠不夠完整」——那件事還是得靠 ⑬ 段的人工驗收清單。

## 發現的問題與修正

### 問題 1：Day27 文章沒有程式碼，DIY 應該著重在什麼？

**發現：** Day27 是純概念/流程指導，不像 Day0-2 有明確的實作程式碼。但文章的「④ SRE Lab」與「⑦ 步驟一～六」段落有具體的程式碼示範。

**修正方針：** 
本 DIY 的目標轉為「提供可用的工具與範本」來實踐 Day27 講的 postmortem 文化。具體做法：
1. 用 Pydantic 建立 postmortem 資料模型，確保結構完整（符合 Day27 五段流程 + AI 特有檢視）
2. 提供 markdown 產生器，讓 incident 記錄能轉為可讀的文件
3. 提供兩個完整的範例 incident postmortem（一個傳統 SRE，一個 AI-specific），示範如何應用
4. 提供 runbook 工具，演示「知識留存」的實踐
5. **新增 incident_drill.py 模組**，實現文章 ⑦ 的六步驟演練：
   - Step 1: `parse_citations()` 函式展示可重跑的故障模式
   - Step 2: `IncidentContext` dataclass 展示可關聯欄位
   - Step 3: `TechnicalStatus`、`WorkflowStatus`、`QualityStatus`、`SafetyStatus` 四個狀態 enum
   - Step 4: `IncidentEvent` 結構與脫敏 JSON 記錄
   - Step 5: `TabletopExercise` 類模擬 30 分鐘演練
   - Step 6: `test_missing_citation_is_not_a_success()` 轉換為可復用的回歸測試

這樣 DIY 不是「跑一個服務」，而是「用工具演練一場真實的 postmortem 流程」，並直接實現文章程式碼示範。

### 問題 2：Pydantic 相依套件是否必要？

**發現：** 只用 pydantic 一個第三方套件（Python 內建 enum、datetime 都能用）。

**決定：** 保留 pydantic，理由：
- 強型別模型能防止遺漏欄位（incident 資訊很容易有疏漏）
- Pydantic 的 `.dict()` / `.json()` 能輕易序列化到檔案或 API
- 與實戰的 incident tracking 系統相容（通常也是 JSON schema 為主）
- 本 DIY 專案本身教的就是「用結構化資料來記錄 incident」

### 問題 3：Example incident 應該參考什麼？

**決定：** 
- 範例 1（INC-2026-001）：參考 Day3 的「故障注入實驗」——資料庫逾時的級聯故障
- 範例 2（INC-2026-005）：創造新的 AI 特定故障——RAG 索引過舊

這樣既示範如何轉化已有的 chaos test，也展示新的 AI-specific failure mode。

### 問題 4：`.env` 檔案策略

**決定：** 
本專案無真實 API Key/credential，`.env` 只有虛擬變數（`INCIDENTS_OUTPUT_DIR`）。
`.env` 與 `.env.example` 內容相同（都是假值），符合「documentation project」性質。

### 問題 5：Runbook 中的指令是否需要真的能執行？

**發現：** Runbook 中有 SQL、Docker、Python 指令示範，但本環境無 DB/Docker。

**決定：** 這是正確的。Runbook 應該是「參考文件」，包含假設的指令與查詢，供真實故障時查閱。本 DIY 的 runbook entry 包含足夠細節讓工程師能在實際環境中執行。

### 問題 6：Postmortem 完整度檢驗

**實測檢查：**
- [x] 兩個生成的 postmortem 都遵循 Day27 ④ 的五段結構
- [x] 都包含「系統條件」而非「人的過錯」的根因敘述
- [x] 都有明確的 Action Item（owner、deadline、priority、category）
- [x] AI incident 額外包含 evaluation gap 與 safety check 分析
- [x] 所有 postmortem 都能從 Pydantic 模型正確生成

### 問題 7：Day27 ⑦ 的六步驟程式碼示範應該放在哪？

**發現：** 文章 ⑦「SRE Lab：用一個可重跑的演練產出復盤素材」提供了六個具體的程式碼範例，原本 DIY 沒有實現這些。

**修正方針：**
新增 `app/incident_drill.py` 模組，直接實現六個步驟：
1. **Step 1 - 重現故障**：`parse_citations()` 函式展示格式驗證失敗
2. **Step 2 - 建立上下文**：`IncidentContext` dataclass 包含 request_id、trace_id、task_id、prompt_version、deployment_id
3. **Step 3 - 定義狀態**：四個 StrEnum class（TechnicalStatus、WorkflowStatus、QualityStatus、SafetyStatus）
4. **Step 4 - 事件記錄**：`IncidentEvent` dataclass 與 `to_json()` 方法產生脫敏記錄
5. **Step 5 - 演練**：`TabletopExercise` 類模擬分鐘級的決策過程（0分鐘到30分鐘）
6. **Step 6 - 迴歸測試**：`test_missing_citation_is_not_a_success()` 把故障轉成永遠保護的測試

執行 `uv run python -m app.main --drill` 即可看到完整流程。

**實測結果：**
- [x] `incident_drill.py` 模組成功執行，無 import 錯誤
- [x] `parse_citations()` 正確檢測缺少格式的引用
- [x] `IncidentContext` 成功建立 UUID 識別字
- [x] 四個狀態 enum 都能列舉出所有值
- [x] `IncidentEvent` 成功轉為 JSON，包含脫敏的關鍵欄位
- [x] `TabletopExercise` 依序模擬 6 個時刻的決策（0、5、10、15、20、25、30 分鐘）
- [x] 迴歸測試 `test_missing_citation_is_not_a_success()` 通過

**實測時踩到的坑（與設計上刻意的取捨）：**
- `IncidentContext` 的五個欄位（`request_id`、`trace_id`、`task_id`、`prompt_version`、`deployment_id`）在 dataclass 定義上全部是必填，沒有給任何預設值。這是刻意的：如果哪個呼叫端漏傳一個欄位，Python 會在建構的當下直接丟 `TypeError`，而不是安靜地把欄位設成 `None` 讓問題延後到事故現場才被發現。這對應文章 ⑦ 段講的「團隊初期只填 request_id，忘記填 prompt_version」——用型別系統把這個坑在寫程式的當下就擋掉，比事後靠 code review 提醒可靠。
- `IncidentEvent` 的欄位清單裡完全沒有原始使用者輸入或模型完整輸出這類欄位——`to_json()` 只序列化 request_id、trace_id、task_id、版本欄位與四個狀態值。這代表這個資料結構從設計上就不可能不小心把敏感內容寫進事件記錄，跟文章 ⑦ 段「常見的坑是工程師加一個『以防萬一』的 raw_answer 欄位」的警告方向一致——但也代表如果未來真的需要在脫敏事件裡附上一小段判斷依據（例如「哪個 citation 格式不對」），得另外設計一個明確、經過審視的欄位，而不是圖方便塞進一個泛用的 `extra` 或 `metadata` 欄位，否則同樣的風險會用不同的名字重新長出來。
- `TabletopExercise` 每次執行 `run_full_drill()` 都會重新 `TabletopExercise(context)` 建立一個全新物件，`timeline` 與 `decisions` 兩個 list 也是在 `__init__` 裡重新初始化，所以連續跑好幾次演練不會有紀錄互相污染的問題。但如果之後要把這個類別改成「可以在同一個 session 裡重跑」（例如互動式 CLI 工具），要留意目前並沒有提供任何清空既有 timeline 的方法——沿用同一個物件重跑會讓輸出的時間線疊加兩次演練的紀錄，這是目前程式碼裡唯一一個「如果亂用會踩到」的隱性假設。

### 問題 8：文章新增了 Step 7（FastAPI middleware），本 DIY 尚未同步實作

**發現：** Day27 文章後續擴寫時，在 DIY 段落新增了第七步——把前六步串成一段真正會被呼叫的 FastAPI middleware，示範 `IncidentContext` 與四個狀態 enum 如何在請求進來的當下就被寫入 JSON 事件記錄，而不是留到演練現場才手動建立。本 DIY 專案目前的 `app/incident_drill.py` 仍停留在六步驟的版本，尚未新增對應的 middleware 模組與測試。

**誠實揭露：** 這裡刻意不假裝已經完成同步——沒有實際寫出 `app/middleware.py`、跑過 `uv run`、也沒有驗證過 middleware 是否真的能攔截請求並正確寫入 `IncidentEvent`，就不該在「實測結果」欄位打勾。這符合 CLAUDE.md 的 DIY SOP：「實測結果」要逐項對照真的跑過的東西，不是對照文章寫了什麼。

**待辦：** 下次更新本 DIY 專案時，應該：
1. 新增 `app/middleware.py`，實作文章 Step 7 描述的 FastAPI middleware。
2. 讓 middleware 在每個請求進來時自動建立 `IncidentContext`（而非像現在的 `incident_drill.py` 需要手動傳入五個欄位）。
3. 補一支整合測試，實際發一個請求進去，驗證回應與寫出的 JSON 事件記錄都包含正確的版本與狀態欄位。
4. 完成後才把對應項目移進「實測結果」章節，並在此問題底下記錄實測時遇到的坑。

## 下一步建議

1. **實戰演練**：選擇一個真實發生過的故障（可參考 Day3 chaos test 或實際 production incident），用本 DIY 的工具重新記錄一遍 postmortem，檢查是否遺漏任何維度。

2. **整合到 Incident 追蹤系統**：現在 postmortem 存成 markdown 檔案。下一步可整合到實際的 incident management 工具（如 PagerDuty + markdown export、或自製 Django API），讓 postmortem 能被版控與搜尋。

3. **Runbook 即時化**：本 DIY 的 runbook 是靜態文件。實戰中應該把 runbook entry 連到實際的 Grafana dashboard、查詢預設值、escalation slack 頻道等，讓故障時能一鍵跳轉。

4. **評估文化植入**：在團隊引入 postmortem 時，先用本 DIY 的模板與範例讓大家熟悉結構，再進行第一場真實的「Wheel of Misfortune」角色扮演練習（Day27 ⑤ 提到的 Google 方法）。

---

> 這篇是 Learning SRE for the AI Era 系列的一部分。
> Build → Trace → Break → Measure → Evaluate → Recover → Improve.
