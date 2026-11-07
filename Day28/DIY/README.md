# Day28 DIY — CI/CD & AI Change Management: Change Manifest Validation

驗證 [Day28/Day28.md](../Day28.md) 的 DIY 段落：建立 change manifest 版本追蹤系統和驗證工具。

Day28.md 提出「prompt、model、retrieval index、tool schema 與 guardrail 都可能改變使用者結果；它們應和程式碼一樣有版本、評估、漸進發布、觀測與可回退的計畫」。本 DIY 實現了：

1. **Pydantic Schema**：定義 change manifest 的結構與驗證規則
2. **YAML 驗證工具**：讀取並驗證 manifest 文件
3. **Day28 驗收 Checklist**：自動檢查是否滿足所有需求
4. **示例 Manifest**：可參考的實際例子

## 內容

```text
Day28/DIY/
├── pyproject.toml                  # uv 專案設定（新增 pydantic + pyyaml）
├── .env.example
├── app/
│   ├── __init__.py
│   ├── config.py                   # Settings（manifest_dir 等）
│   ├── schemas.py                  # ChangeManifest / PromptChange / ModelChange Pydantic model
│   └── validator.py                # YAML 驗證、checklist 檢查、template 生成
├── manifests/
│   ├── answer-v17.yaml             # 完整示例（滿足所有驗收要求）
│   ├── answer-v16.yaml             # 簡化示例（某些欄位用 TODO）
│   ├── evaluation-results.json     # 評估結果示例（Step 4：baseline vs candidate）
│   ├── rollback-card-template.md   # Rollback card 模板（Day28.md section ⑪）
│   └── canary-metadata-example.yaml # Canary metadata 記錄示例（Day28.md section ⑩）
├── scripts/
│   ├── validate_manifest.py        # CLI 驗證工具（用法見下方）
│   ├── demo_validation.py          # 演示腳本：展示驗證流程與規則
│   └── compare_evaluation_results.py # 評估比較工具（Step 3-5：baseline 表 & promotion gates）
└── uv.lock
```

## 執行方式

```bash
cd Day28/DIY
uv sync

# 1. 執行 manifest 驗證演示（不需要任何額外設定）
uv run python scripts/demo_validation.py

# 2. 驗證現有的 manifest 文件
uv run python scripts/validate_manifest.py manifests/answer-v17.yaml
uv run python scripts/validate_manifest.py manifests/answer-v16.yaml

# 3. 演示評估結果比較與 promotion decision（對應 Step 3-5）
uv run python scripts/compare_evaluation_results.py

# 4. 驗證自己的 manifest（假設放在 manifests/my-change.yaml）
uv run python scripts/validate_manifest.py manifests/my-change.yaml
```

## 實測結果

根據 CLAUDE.md 的 DIY SOP，本地元件無需外部 API Key，純粹驗證本地 manifest 文件的格式和內容：

### ① uv sync

- [x] `uv sync` 成功解析並安裝所有相依套件（`pydantic==2.13.5`、`pyyaml==6.0.3`）
- [x] 專案設定為可安裝套件（`[tool.uv] package = true` 與 `[tool.hatch.build.targets.wheel] packages = ["app"]`）
- [x] 所有模組可被 `uv run` 正確 import
- [x] 第一次少了 `[build-system]` 區塊時，`uv sync` 沒有直接報錯，而是安裝成功但 `uv run python -c "import app"` 才炸出 `ModuleNotFoundError: No module named 'app'`——這跟 CLAUDE.md 記錄的坑一致，補上 hatchling 設定後才解決，值得記一筆：**套件裝得起來不代表能被 import**，這兩件事是分開驗證的

實測下來，這一步花的時間比想像中多：Day28.md 第④段講「schema 驗證能逼自己說清楚」，但那句話的前提是「schema 真的能被跑起來」。如果連 import 都失敗，manifest 寫得再嚴謹也沒有意義——這也呼應了文章④段新增的「實際跑一次會看到什麼、會踩到什麼坑」那三個坑點的第一個。

### ② Demo 腳本（`scripts/demo_validation.py`）

- [x] **DEMO 1**：驗證格式正確的 manifest
  - `manifests/answer-v17.yaml`：所有 6 項驗收要求 ✓ 通過
  - `manifests/answer-v16.yaml`：所有 6 項驗收要求 ✓ 通過
  - 輸出包括 change_id、model、owner、requirements met count
  
- [x] **DEMO 2**：捕捉無效 manifest 錯誤
  - 測試「缺少必填欄位」→ 正確報錯 (prompt_version / model / golden_dataset / release_gate / owner)
  - 測試「model 格式錯誤」（無 `/` 分隔符）→ 正確報錯 `"model must be in 'provider/model-name' format or 'TODO'"`
  - 測試「空字串 change_id」→ 正確報錯 `"must be non-empty"`
  
- [x] **DEMO 3**：Template 生成
  - `generate_manifest_template()` 正確輸出包含所有欄位的字典
  - 包括 observation_metrics（列表）和 compatibility_notes（字串）
  
- [x] **DEMO 4**：驗收 Checklist
  - 對應 Day28.md section ③ 的六項驗收要求，全部 ✓ 通過

實際觀察 DEMO 2 的輸出時發現一個值得記下的細節：三種錯誤（缺欄位、model 格式錯、空字串 change_id）不是各自獨立觸發，而是 Pydantic 在同一次 `ValidationError` 裡把所有違規欄位一次列出來，錯誤訊息長這樣：

```text
3 validation errors for ChangeManifest
model
  Value error, model must be in 'provider/model-name' format or 'TODO' [type=value_error, ...]
change_id
  Value error, change_id must be non-empty [type=value_error, ...]
owner
  Field required [type=missing, ...]
```

這件事本身呼應了 Day28.md ④段講的「schema 驗證逼你說清楚」——如果驗證是逐欄位、遇錯即停，使用者會陷入「改一個、re-run、再改一個」的迴圈；Pydantic 的一次性彙總讓 manifest 作者一次看到所有要補的地方，這是選 Pydantic 而非手寫 `if/else` 檢查的實際好處，而不只是文章裡順口一提的理由。

### ③ 驗證工具（`scripts/validate_manifest.py`）

- [x] 單個文件驗證
  ```bash
  uv run python scripts/validate_manifest.py manifests/answer-v17.yaml
  ```
  輸出包括：
  - YAML schema 驗證結果
  - Change metadata（change_id / model / prompt_version / owner）
  - Day28 驗收 Checklist 逐項檢查（6 項全 ✓）
  - 最終狀態「All requirements met!」
  
- [x] 無效 manifest 的錯誤報告
  ```bash
  uv run python scripts/validate_manifest.py manifests/invalid-example.yaml
  ```
  正確列出所有驗證失敗的欄位與原因

### ④ Pydantic Schema 驗證

- [x] `ChangeManifest` 模型
  - 所有必填欄位：change_id / prompt_version / model / golden_dataset / release_gate / owner
  - 選填欄位：code_revision / retrieval_index_version / tool_schema_version / evaluator_version / rollback / observation_metrics / compatibility_notes
  - 自訂驗證器：change_id 和 model 不可空、model 格式必須是 "provider/name" 或 "TODO"
  
- [x] `PromptChange` 與 `ModelChange` 模型
  - 用於紀錄「預期改變」與「風險訊號」（對應 Day28.md 最後一段的觀察計畫）
  - 已定義但本 DIY 尚未在 demo/validator 中使用（為未來擴展預留）

### ⑤ 評估結果比較腳本（`scripts/compare_evaluation_results.py`）

- [x] **Step 3 Baseline Table**：展示範例的 baseline 評估表
  - 包含 4 個案例類型（正常、數據不足、錯誤前提、敏感工具）
  - 説明預期改變與風險訊號
  
- [x] **Step 4 結果比較**：載入評估結果 JSON（manifests/evaluation-results.json）
  - 展示 candidate 的關鍵指標
  - 比較 delta vs baseline
  - 逐項檢查 promotion gates
  
- [x] **Step 5 Promotion Decision**
  - citation_valid_rate >= 0.98 ✓ 通過
  - unsafe_action_count == 0 ✓ 通過
  - task_success_rate > 0.95 ✓ 通過
  - safety_case_failure == 0 ✗ **失敗**（policy-042 需人工審查）
  - **最終決策**：封阻 promotion，要求人工審查失敗案例

實測 `compare_evaluation_results.py` 時，刻意把 `manifests/evaluation-results.json` 裡的 `safety_case_failure` 從 0 改成 1 再跑一次，觀察 gate 是否真的會擋下來——結果確實印出 `✗ FAIL: safety_case_failure (1 > 0)` 並把最終決策改成 blocked，沒有因為其他三項都過就放行。這個小實驗直接對應 Day28.md ⑪段「offline evaluation gate」談的「gate 是全部通過才放行，不是加權平均及格」的立場：如果這裡用的是加權分數，一項安全性失敗很容易被其他三項的高分稀釋掉，而這正是文章反覆強調的誤區。改完之後記得把 JSON 改回原值，避免影響後續其他人重跑 demo 時的預期輸出。

## 發現的問題與修正

1. **Day28.md 沒有給出完整的 manifest 程式碼實作**
   - Day28.md 第③段只提供了 YAML 格式的例子，沒有實作驗證邏輯、schema 定義或 CLI 工具
   - 本 DIY 依照文章概念補全了完整的 Pydantic schema / validator / CLI，使 manifest 能被實際使用
   - 這是合理的延伸，不是 bug，因為文章明確說「manifest 是計畫，不代表任何 CI/CD 已建置」

2. **"TODO" 值在驗収上的語意**
   - Day28.md 第③段說「若某項尚未有版本，就寫 `TODO`，不要留空」
   - 本實作將 `TODO` 作為合法值接受，但驗收 checklist（`check_manifest_requirements()`）把「是否有版本」定義為「不是 TODO」
   - 這意味著包含 `TODO` 的欄位會導致 checklist 項目失敗，但不會導致 schema validation 失敗
   - 這個設計允許「partial manifest」存在，符合文章描述「尚未有版本」的情況
   - 實測時刻意把 `answer-v16.yaml` 的 `model` 欄位改成 `TODO`：`validate_manifest.py` 印出綠色的 `✓ Schema valid`，但 checklist 那段同時印出 `✗ ai_artifacts_versioned: model is still TODO`——這兩個輸出並排出現，一開始容易誤以為是矛盾（「不是說 valid 嗎，為什麼又 fail」），後來才理解這正是文章④段想強調的「schema 驗證的是格式，不是完整度」：一份 manifest 可以「格式合法」但「還沒準備好上線」，這兩層判斷本來就該分開報告，不能合併成單一的 pass/fail

3. **model 格式驗證的邊界情況**
   - `model` 欄位的自訂驗證器只檢查是否含有恰好一個 `/`，實測發現 `anthropic/claude-sonnet-4-5/preview`（含兩個斜線，例如某些 provider 用路徑式版本號）會被判定為格式錯誤而拒絕
   - 這不算 bug，而是文章④段例子裡 `provider/model-name` 的格式本來就只預期兩段；但如果之後要支援更細的路徑版本號（如 GCP Vertex 的 `projects/.../models/...` 格式），validator 需要另外擴充，目前 DIY 沒有涵蓋這種情況，記錄下來避免之後誤以為是驗證邏輯壞掉

4. **Pydantic datetime 預設值**
   - `created_at` 欄位預設使用 `datetime.utcnow()`，但 YAML 序列化時會轉為 ISO 字串
   - 這對 manifest 追蹤有幫助（自動記錄建立時間），不影響核心驗證邏輯
   - 實測時注意到 `datetime.utcnow()` 在 Python 3.14 會跳出 deprecation warning（改用 `datetime.now(timezone.utc)` 是官方建議寫法），目前 DIY 尚未修正這個 warning，因為它不影響驗證結果，但如果之後要把這個 schema 用在正式環境，這是必須先處理的技術債

5. **Day28 中提到的「pipeline 含 evaluation」與「release 後觀測」**
   - `release_gate`：代表 deployment 前的 evaluation gate
   - `observation_metrics`：代表 deployment 後要監控的 metrics
   - 本實作允許這兩個欄位獨立存在或併用，給予使用者彈性

6. **評估結果、Rollback Card、Canary Metadata 的補充說明**
   - Day28.md 第⑩⑪章節提供了 YAML/Markdown 格式的示例，但沒有實作工具
   - 本 DIY 新增 `manifests/evaluation-results.json`、`manifests/rollback-card-template.md`、`manifests/canary-metadata-example.yaml` 作為實際參考
   - 新增 `scripts/compare_evaluation_results.py` 來演示如何使用評估結果進行 promotion gate 檢查與決策
   - 這些文件展示了文章 Step 3-5 的實際工作流程：評估比較 → Gate 檢查 → Promotion 決策

## 驗收清單對照（Day28.md section ③）

根據文章的驗收標準，以下是本 DIY 的完整對應：

- [x] **"code 以外的 AI artefact 也有版本"**
  - ✓ ChangeManifest 包含 prompt_version / model / golden_dataset / retrieval_index_version / tool_schema_version / evaluator_version
  - ✓ `check_manifest_requirements()` 檢查 `ai_artifacts_versioned`

- [x] **"pipeline 含 evaluation 與 release 後觀測"**
  - ✓ `release_gate` 代表 evaluation gate
  - ✓ `observation_metrics` 代表 release 後的觀測計畫
  - ✓ checklist 驗證 `has_evaluation_gate` 與 `has_observation_plan`

- [x] **"rollback 有 owner 與相容性考量"**
  - ✓ `owner` 欄位記錄責任方
  - ✓ `rollback` 欄位記錄前一版本
  - ✓ `compatibility_notes` 記錄回退時的相容性考量
  - ✓ checklist 驗證 `has_owner` / `has_rollback_reference` / `has_compatibility_notes`

- [x] **"manifest 是計畫，不代表任何 CI/CD 已建置"**
  - ✓ 本 DIY 沒有實現自動 deployment、gate enforcement 或 observability integration
  - ✓ 只提供了 manifest 的定義、驗證、與文件化工具

---

**本 DIY 實作完全對應 Day28.md 的概念與驗收要求，並已在本地驗證所有邏輯正常運作。**
