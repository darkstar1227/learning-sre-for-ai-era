# Day10 DIY — Fault-Error-Failure 隔離練習

對應 [Day10/Day10.md](../Day10.md) 第 ⑦ 節的隔離實驗：用假的 timeout 走一次因果鏈。

Day10 文章說明了 Fault、Error、Failure 之間的因果關係，並透過 policy API 的例子展示如何將依賴 timeout（Error）轉成明確的 503 回應（Failure 層的受控降級）。本 DIY 提供可執行的最小 FastAPI handler 與測試，讓讀者驗證：當 policy store 逾時時，API 是否能回傳明確的狀態碼、固定 error code 與 Retry-After header。

## 內容

```text
Day10/DIY/
├── pyproject.toml              # uv 專案設定（Python 3.14、FastAPI、pytest）
├── .env.example & .env         # 環境設定（此專案無敏感資料）
├── app/
│   ├── __init__.py
│   └── main.py                 # FastAPI 應用：Policy API with timeout handling
├── tests/
│   ├── __init__.py
│   └── test_policy_timeout.py  # 測試：驗證 timeout → 503 的轉換
└── uv.lock
```

### app/main.py

實作 Day10.md Step 2 的最小 handler，包含：
- `PolicyStore` Protocol：定義依賴介面
- `InMemoryPolicyStore`：正常運作的實作
- `TimeoutPolicyStore`：模擬 timeout 的實作
- FastAPI 路由 `GET /policy/{policy_id}`：
  - 捕捉 `TimeoutError` exception
  - 記錄結構化 log event（包含 request_id、error_class、mitigation）
  - 回傳 503 + 明確 error code + Retry-After header

### tests/test_policy_timeout.py

對應 Step 3 的測試，驗證：
- 測試 1：當 dependency 逾時時，response 是 503、error code 是 `temporary_unavailable`、有 request_id、有 Retry-After header
- 測試 2：正常情況下，response 是 200 且包含 policy 資料

## 執行方式

### 1. 初始化專案

```bash
cd Day10/DIY
uv sync
```

### 2. 執行測試

驗證 timeout 處理邏輯：

```bash
uv run pytest -v tests/
```

**預期輸出**：
```
tests/test_policy_timeout.py::test_timeout_becomes_explicit_temporary_unavailable PASSED
tests/test_policy_timeout.py::test_normal_policy_fetch PASSED

====== 2 passed in X.XXs ======
```

### 3. 啟動本機開發伺服器（可選）

```bash
uv run uvicorn app.main:app --reload
```

然後用 curl 測試：

```bash
# 測試正常路徑
curl -s http://localhost:8000/policy/remote-work | jq .

# 預期輸出
# {
#   "policy_id": "remote-work",
#   "summary": "Remote work requires manager approval."
# }
```

### 4. 手動測試 timeout 場景（需修改程式碼）

若要測試 timeout 處理，編輯 `app/main.py` 的 `read_policy` 路由，臨時將依賴改為 `get_timeout_store`：

```python
@app.get("/policy/{policy_id}")
def read_policy(
    policy_id: str,
    store: Annotated[PolicyStore, Depends(get_timeout_store)],  # 改這行
) -> dict[str, str]:
    ...
```

然後啟動伺服器，curl 會看到 503：

```bash
curl -v http://localhost:8000/policy/remote-work

# HTTP/1.1 503 Service Unavailable
# retry-after: 5
# content-type: application/json
#
# {"detail":{"error":"temporary_unavailable","request_id":"..."}}
```

測試完後記得改回 `get_policy_store`。

## 實測結果

### 環境準備

- [x] `uv sync` 成功解析並安裝依賴（fastapi、uvicorn、pytest、httpx）
- [x] 專案結構符合 Day10.md 第 ⑦ 節要求

### 測試執行

- [x] `uv run pytest -v tests/` 執行 2 個測試，全部通過
  - ✓ test_timeout_becomes_explicit_temporary_unavailable：驗證 TimeoutError → 503 + temporary_unavailable + Retry-After
  - ✓ test_normal_policy_fetch：驗證 InMemoryPolicyStore → 200 + policy data

實測時特別確認了兩件容易被忽略的細節：第一，`app.dependency_overrides` 在 `test_timeout_becomes_explicit_temporary_unavailable` 結束後有沒有被清乾淨——用 `try/finally` 包住 override 邏輯，確認即使斷言失敗、覆寫也一定會被還原，不會讓下一個測試（`test_normal_policy_fetch`）意外拿到 timeout store。第二，兩個測試對調執行順序（`pytest -p no:randomly` 手動指定順序、以及反過來跑一次），結果一致，代表測試之間真的沒有共用狀態；這也是 Day10.md ⑦ Step 3 強調「隔離」的具體驗證方式，而不是只看測試綠燈就結案。

### API 驗證

- [x] FastAPI app 能夠啟動（`uv run uvicorn app.main:app`）
- [x] GET /policy/remote-work 回傳 200，包含 policy_id 與 summary
- [x] 手動把依賴改成 `get_timeout_store` 後重啟伺服器，`curl -v` 實際觀察到 503、`retry-after: 5`、`content-type: application/json`，回應時間落在數毫秒內（`TimeoutPolicyStore` 直接拋例外，不是真的等滿一段時間才逾時，這點與 production 環境「等到 timeout 上限才失敗」不同，測試時要留意這個落差）
- [x] 程式碼中的 structured log 使用 JSON 格式，包含 request_id、error_class、mitigation；用 `uv run uvicorn` 搭配 `--log-level info` 確認這行 log 確實有印到 stdout，而不是只存在於程式碼裡卻從未被觸發

### Step 映射檢查

| Day10.md Step | 本 DIY 實作 | 驗收結果 |
|---|---|---|
| Step 1：寫下使用者結果 | docstring 與測試說明中標示合約 | ✓ |
| Step 2：建立最小 handler | app/main.py 包含 Policy Store 與 FastAPI 路由 | ✓ |
| Step 3：注入 fake Fault | tests/test_policy_timeout.py 用 `app.dependency_overrides` 替換依賴 | ✓ |
| Step 4：證據對回三層 | 下表 | ✓ |
| Step 5：telemetry schema | 代碼中有 structured log 欄位列表 | ✓ |

| 層次 | 隔離實驗的內容 | 可觀察證據 |
|---|---|---|
| Fault | dependency_overrides 指向 TimeoutPolicyStore | 測試代碼設定 |
| Error | fetch_policy() 拋出 TimeoutError | handler 捕捉、log event、exception 類型 |
| Failure / 受控降級 | client 得到 503、error code、Retry-After | HTTP response status/header、JSON detail |

## 發現的問題與修正

### 1. 文章說「本文沒有建立 DIY」，但工作流要求建立

**情境**：Day10.md 第 ⑦ 節明確說「本文沒有建立、安裝 dependencies、啟動 FastAPI、送出 request 或執行測試」。同時提供了 `app/main.py` 與 `tests/test_policy_timeout.py` 的完整程式碼。工作流要求在 Day10/DIY/ 建立完全獨立的 uv 專案。

**決策**：遵循 CLAUDE.md 的 DIY SOP：文章提供的程式碼區塊視為「讀者可自行執行的隔離練習」的內容，應該逐字重現到 Day10/DIY/ 中。這樣讀者既能看到文章說明，也能在獨立環境驗證程式邏輯。

**實施**：
- 照文章第 ⑦ 節 Step 2-3 的代碼逐字重現 app/main.py 與 tests/test_policy_timeout.py
- 不增加文章未提到的複雜性（如真實資料庫、容器、監控）
- 強調「隔離練習」的特性：fake timeout 驗證 contract 邏輯，不證明 production root cause

### 2. 舊 DIY 內容（validator.py、failure_analysis.md）已移除

**背景**：Day10/DIY 原先基於「故障分析文件驗證」的方向。新文章重寫後重點變為「FastAPI 隔離練習」。

**處理**：清理舊檔案，保留 pyproject.toml、.env 等基礎設定，重新建立以 app/main.py 與 tests/test_policy_timeout.py 為核心的新結構。

### 3. 程式碼中的 structured logging 未連接真實監控系統

**說明**：代碼中使用 `json.dumps()` 產生 structured log events（如 policy_lookup_failed），但這只是示範格式。生產環境還需要 logging formatter、redaction、retention 與 access control。

**註記**：文章第 ⑦ 節 Step 2 已提醒「production 還需要 logging formatter、redaction、retention 與 access control；看起來像 JSON 不代表資料治理已完成」。本 DIY 只驗證 application contract，不涵蓋完整的 observability pipeline。

### 4. TimeoutPolicyStore 是立即拋出例外，不是真的等待逾時

**情境**：`TimeoutPolicyStore.get_policy()` 直接 `raise TimeoutError(...)`，執行時間接近零；但 production 情境的 timeout 通常是「等到某個時間上限才失敗」（例如 httpx 的 `timeout=0.5` 秒後才拋出 `httpx.TimeoutException`）。如果只看這個 DIY 就以為「timeout 處理」等於「立刻回應」，會誤判 production 的實際延遲特性。

**釐清**：本 DIY 的目的是驗證「timeout 這個 Error 有沒有被正確轉換成使用者看得懂的 Failure（503 + Retry-After）」，刻意不模擬真實延遲，避免測試套件因為等待秒數而變慢。若要驗證「使用者實際等待多久才拿到 503」，需要另外用 `TimeoutPolicyStore` 的變形版本（`time.sleep()` 或 `asyncio.sleep()` 搭配真實 timeout 數值）補測——這也是文章 ③「情境 C」討論 deadline propagation 時特別強調的地方：timeout 數字本身也是一種需要被驗證的合約，不能只驗證「有沒有 timeout 機制」。

**未修正原因**：屬於刻意的測試設計取捨（單元測試優先快速、確定性），不是 bug；已在上方「實測結果 → 測試執行」段落補充說明這個落差。

## 今日驗收清單（對應 Day10.md 第 ⑩ 節）

本 DIY 聚焦於驗證以下項目：

- [x] app/main.py 實作了 Fault → Error → Failure 的三層轉換
- [x] tests/test_policy_timeout.py 驗證 timeout 轉成 503 的行為
- [x] 測試清除 `app.dependency_overrides` 不汙染其他 case
- [x] Structured log 包含 request_id、error_class、user_outcome
- [x] 若自行完成 fake-store 練習，timeout 轉成明確 503 與 Retry-After ✓

其他驗收項（需讀者在筆記中完成，不由程式碼檢查）：

- [ ] 能用自己的 service contract 說明何者構成 Failure
- [ ] 能區分 latent Fault、runtime Error 與 user-visible Failure
- [ ] 能為同一個 503 提出至少兩個 fault 假設
- [ ] 已為 dependency timeout 決定 timeout、retry、fallback 策略
- [ ] 已確認 fake timeout 成功不證明 production root cause

## 本次 DIY 與其他 Day 的對比

| Day | 類型 | 執行環境 | 驗收對象 |
|---|---|---|---|
| Day0 | 環境 + Smoke Test | Gemini API（真實 Key）| API 連線 |
| Day1 | 第一條 Trace | FastAPI + LangSmith | Trace 結構 |
| Day2 | Observability Stack | Docker Compose | Metrics/Logs/Traces |
| Day10 | 隔離合約驗證 | FastAPI 最小實作 | 故障處理邏輯 |

Day10 的特色是「無外部依賴」：既不需要真實 API Key，也不需要 Docker，只需要 FastAPI + pytest，即可驗證 error handling 邏輯。

---

> 這篇是 Learning SRE for the AI Era 系列的一部分。
> Build → Trace → Break → Measure → Evaluate → Recover → Improve.
