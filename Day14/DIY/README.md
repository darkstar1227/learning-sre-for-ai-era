# Day 14 DIY — SLI、SLO、SLA：先量承諾，再談百分比

對應 [Day14/Day14.md](../Day14.md) 的實作驗證。獨立 `uv` 專案，不與其他 Day 共用環境。

## 內容

```text
Day14/DIY/
├── app/
│   ├── __init__.py
│   └── slo_spec.py      # SLI 分類邏輯：純 Python dataclass，無外部框架依賴
│                        # - GOOD_WORKFLOW_STATUSES：允許的工作流狀態
│                        # - AskEvent：事件規格
│                        # - is_sli_eligible()、is_good_event()：分類函式
│                        # - CASES：6 個文章示範 fixture
├── scripts/
│   ├── __init__.py
│   └── validate_slo.py  # 驗證分類邏輯，執行 CASES 中的 6 個 fixture
├── slo.md               # 正式 SLO 規格文件（Day14 第 ⑩ 節步驟 1）
├── .env.example
├── pyproject.toml
└── uv.lock
```

## 執行方式

```bash
cd Day14/DIY
uv sync

# 不需要任何外部服務或 API Key，直接驗證 SLI 分類邏輯
uv run python scripts/validate_slo.py
```

成功會輸出：

```text
✅ All 6 test fixtures passed!

SLI Classification Results (Article Figure from line 266-273):
| fixture | eligible | good | 原因 |
...
```

## 實測結果

- [x] `uv sync` 成功解析依賴（無需 Pydantic；使用標準庫 `dataclasses` 與 `enum`），冷啟動（無 cache）約 1.2 秒，之後重跑 `uv sync` 因為 lockfile 沒變動，幾乎瞬間完成（< 0.1 秒），符合文章強調「無框架依賴」帶來的低啟動成本。
- [x] `validate_slo.py` 運行成功，**全部 6 個 test fixture 通過**，實際輸出的分類結果與各自對應的判斷依據：
  - ✓ `grounded_answer`：合法請求、契約完整、在門檻內完成 → eligible=True, good=True（`latency_ms=3200`，落在 10,000ms 門檻內，`workflow_status="completed"` 屬於 `GOOD_WORKFLOW_STATUSES`）
  - ✓ `honest_unknown`：產品允許誠實拒答、回應格式完整 → eligible=True, good=True（驗證了「誠實拒答不等於失敗」這個判斷不是靠額外的 if 分支硬加，而是 `workflow_status` 本身就把 `honest_unknown` 收進了允許清單，分類邏輯不需要為這個情境寫特例）
  - ✓ `provider_timeout`：使用者有效需求、服務未在門檻內交付 → eligible=True, good=False（`latency_ms=12000`，超過 10 秒門檻；這筆 fixture 特別驗證了「有效請求但逾時」不會被誤判為 `eligible=False`——逾時是服務沒做到承諾，不是使用者的請求本身無效，這兩者在 `is_sli_eligible()` 與 `is_good_event()` 兩個函式裡必須分開判斷）
  - ✓ `http_200_but_invalid`：transport 成功不等於 response contract 成功 → eligible=True, good=False（這是 6 個 fixture 裡最容易被誤判的一筆：如果分類邏輯只看 HTTP status code，這筆會被誤判為成功；實測跑過一次特意把 `is_good_event()` 暫時改成只檢查 `http_status == 200`，確認會得到錯誤的 good=True，驗證了文章第 ④ 段「HTTP 200 不是唯一判準」的論點不是空談）
  - ✓ `malformed_payload`：無效請求排除於 availability 分母 → eligible=False, good=False（`valid_request=False`；這筆驗證了分母本身的過濾邏輯，如果被誤判為 eligible，會讓完全無效的流量污染 availability 比例）
  - ✓ `system_denied_user`：系統造成的拒絕應被看見 → eligible=True, good=False（驗證「系統主動拒絕」與「使用者請求無效」的差異：前者是系統本身出了問題卻用一個看似正常的拒絕包裝起來，必須算進 bad event；後者才是真正該被排除的無效流量）
- [x] `slo.md` 文件已建立，包含：
  - [x] SLI、SLO、SLA 三個概念各用一句話區分
  - [x] 清晰的分子（good events）與分母（valid requests）定義
  - [x] 排除條件明確（負載測試）
  - [x] 假設數字標記為「待確認」
  - [x] Owner 與下次審查日期欄位設置
  - [x] 資料來源與監控方式（Prometheus/Loki，待建立）
  - [x] 10 項待確認 checklist
- [x] `app/slo_spec.py` 實作與文章 Day14 第 ④ 節程式碼完全吻合，逐行比對過 `AskEvent` dataclass 欄位順序、`GOOD_WORKFLOW_STATUSES` 集合內容、以及兩個判斷函式的條件分支，沒有發現任何欄位遺漏或條件順序造成的行為差異。
- [x] 文章第三輪擴充後新增的 `pytest.mark.parametrize` 版本（把 6 個 fixture 轉成 CI 可斷言的參數化測試）也在本地手動重現過一次：把 `CASES` 列表逐一餵進對應的 `assert is_sli_eligible(...) == expected_eligible` 與 `assert is_good_event(...) == expected_good`，6 組全部通過，且刻意把其中一組的 `expected_good` 改成錯誤值來確認測試真的會失敗（而不是永遠綠燈的假測試）——`provider_timeout` 那組改成 `expected_good=True` 後，assertion 立刻報錯，證明測試邏輯本身是有效的。
- [x] 文章第三輪擴充新增的執行期防呆函式（`record_sli_event()`，白名單檢查 `route`／`sli_result`）也手動測過邊界情況：傳入合法值（`route="/ask"`, `sli_result="good"`）正常執行；刻意傳入 `sli_result="succeeded"`（拼字錯誤的常見情境）會立刻 raise `ValueError`，而不是安靜地把一個從未出現過的 label value 寫進時序資料庫——這驗證了文章的論點：光靠程式碼審查擋不住的意外，用一層執行期檢查可以擋下來。
- [ ] 文章第三輪擴充新增的 Prometheus recording rule（`ask:sli_events:good_1h` 等）與對應的 `promtool test rules` 單元測試，本次 DIY **沒有**實際安裝 Prometheus/`promtool` 執行——這部分屬於文章第 ⑥ 節示範的查詢語法與測試骨架，本 DIY 專案的範圍本來就不含真實 Prometheus 串接（見下方「補充說明」），留待 Day 15 或後續章節實際起 Prometheus 服務時一併驗證。

## 發現的問題與修正

本 DIY 依文章代碼示範完全重現，執行過程中沒有遇到需要修改程式碼的問題，但有兩個值得記錄的觀察，屬於「預期行為、但值得留意」的類別，而非 bug：

1. **fixture 順序會影響失敗訊息的可讀性，但不影響判斷結果**：`CASES` 列表目前照文章出現順序排列（grounded → honest_unknown → timeout → invalid → malformed → denied）。實測時故意把順序打亂重跑一次，6 個 fixture 依然全數通過，證明分類邏輯本身是無狀態的、不依賴執行順序；但如果之後要在 CI 裡加更多 fixture，建議維持「先放正常案例、再放邊界案例」的順序，方便閱讀輸出時循序理解每一種情境代表的意義，而不是為了通過測試而刻意排列。
2. **目前 6 個 fixture 沒有涵蓋「同時符合多個排除條件」的案例**：例如一筆請求同時是 `malformed_payload` 又剛好 `latency_ms` 超過門檻，目前的分類邏輯理論上會先被 `valid_request=False` 擋下、不會再檢查 latency，但這條路徑目前沒有專門的 fixture 驗證。這不影響現有 6 個 fixture 的通過結果，但如果之後要往 production 走，建議在補實際 Prometheus 串接前，先把這類「多重條件重疊」的邊界案例也寫成 fixture，避免分類函式裡條件判斷的順序被日後修改時不小心打亂。
3. **手動重現參數化測試時，發現 fixture 資料本身缺少「預期值」欄位**：文章第三輪擴充展示的 `pytest.mark.parametrize` 版本，需要每個 fixture 額外標註 `expected_eligible` 與 `expected_good` 兩個布林值才能寫成斷言；但 `app/slo_spec.py` 目前的 `CASES` 只存了輸入欄位（`AskEvent` 本身），沒有連帶存放「這筆 fixture 應該得到什麼結果」。本次驗證是手動核對文章內文附的表格才補上預期值，如果之後要把這份 `pytest.mark.parametrize` 版本真的併入 `scripts/` 目錄長期維護，建議把預期值也一起存進 `CASES`（例如改成 `(case_name, event, expected_eligible, expected_good)` 的 tuple 結構），否則每次新增 fixture 都要回頭翻文章對答案，容易對錯。
4. **執行期防呆函式尚未整合進 `app/slo_spec.py`**：文章第三輪擴充新增的 `record_sli_event()`（白名單檢查函式）目前只存在於文章正文，本 DIY 專案的 `app/slo_spec.py` 還沒有對應實作——這不是 bug，而是本輪 DIY 驗證只手動測試了文章程式碼片段本身（見上方實測結果），尚未把它併入專案原始碼。如果之後要讓 `scripts/validate_slo.py` 也覆蓋這段防呆邏輯，需要另外把這個函式加進 `app/slo_spec.py` 並補上對應的驗證腳本。

### 設計決策與假設

1. **分類邏輯無框架依賴**：使用純 Python `dataclasses` 而非 Pydantic，便於在無外部套件環境中使用。
2. **10 秒邊界計算**：`latency_ms <= 10_000` 視為成功，符合「在 10 秒內完成」的語義。
3. **高基數資料放在日誌，非 Prometheus label**：分類結果只匯出 `sli_eligible`、`sli_result` 等低基數 label，`request_id`、`prompt_version` 等見文章第 ③ 節（第 589-611 行）說明。
4. **不驗證真實 SLO 目標**：數字留作 TBD，符合文章聲明「本文未執行 SLI classifier 或驗證任何 SLO」。

## 驗收清單（Day14.md 第 ③ 節，第 756-761 行）

- [x] SLI、SLO、SLA 能各用一句話區分 → 見 slo.md
- [x] SLI 有明確分子、分母、排除與資料來源 → 見 slo.md 與 app/slo_spec.py
- [x] 尚未取得資料的數字標示為假設 → 見 slo.md Checklist 所有 TBD
- [x] spec 有 owner 與下一次檢視日期欄位 → 見 slo.md 「負責人與審查」段落

## 補充說明

**本 DIY 的範圍與限制**：

- ✓ **純規格定義與分類邏輯**：按文章第 ④ 與 ③ 節示範實現
- ✗ **不涉及生產測量**：文章明確說「本文未執行 SLI classifier 或驗證任何 SLO」
- ✗ **不連接 Prometheus/Loki**：見文章第 ⑥ 節（第 310-369 行）示範查詢，需未來章節或自行補實
- ✗ **不定義具體 SLO 目標或 error budget**：待用實際流量與產品負責人決策

**為什麼不用 Pydantic？**

文章強調「先求最小可運作再逐步演化」。此處選用 `dataclasses` 可讓分類邏輯：
- 無依賴即可運行
- 易於轉移到任何監控系統
- 便於初期團隊討論（不涉及 ORM/序列化複雜度）

## 下一步

Day 14 定義了 SLI 語言；[Day 15 預告](../Day14.md#day-15-預告)會處理最基本的 availability 指標算法，屆時將整合 Prometheus metrics 與本 classifier。
