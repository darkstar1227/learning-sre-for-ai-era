# Day 08 DIY — Response Evaluation Pipeline（Reliability / Quality / Safety）

驗證 [Day8.md](../Day8.md) 的 DIY 段落：把文章的三軸評估模型接到 Day7 的 `/ask` API 上。

Day8.md 本文明確聲明「本文沒有建立 `Day8/DIY`、安裝依賴、啟動服務或執行以下檢查，因此不宣稱任何程式已驗證」。本目錄依 repo `CLAUDE.md` 的 DIY SOP，把文章段落④⑤⑥⑦描述的 Quality/Safety checks 與 evaluation pipeline，從零建成一個獨立、可執行、已跑過的 uv 專案。

## 內容

```text
Day8/DIY/
├── pyproject.toml            # 獨立 uv 專案設定（新增 prometheus-client）
├── .env.example
├── data/
│   ├── company_policy.md     # 沿用 Day7 的知識範圍
│   └── golden_dataset.json   # Day7 的 4 個案例，加上 expected_facts / risk_level
├── app/
│   ├── config.py              # 沿用 Day7，pydantic-settings 讀 GEMINI_API_KEY
│   ├── documents.py            # 沿用 Day7
│   ├── retrieval.py             # 沿用 Day7
│   ├── prompt.py                 # 沿用 Day7
│   ├── schemas.py                 # TechnicalStatus/QualityStatus/SafetyStatus + 新版 AskResponse
│   ├── llm.py                      # ask_grounded() 改回傳 RawAskResult，交給 evaluation.py 分類
│   ├── quality_checks.py            # 文章⑤的 4 個 Quality checks
│   ├── safety_checks.py              # 文章⑥的 3 個 Safety checks
│   ├── risk.py                        # 極簡關鍵字風險分級，供 Safety Check 3 使用
│   ├── metrics.py                      # 文章⑦的 3 個 Counter（低基數 label）
│   ├── logging_utils.py                # 文章⑦的 structured log（單行 JSON）
│   ├── evaluation.py                    # 文章④的 pipeline：Retriever→LLM→Quality→Safety→Classification
│   └── main.py                           # FastAPI：GET /healthz、POST /ask、GET /metrics
└── scripts/
    ├── run_golden.py                      # 跑 golden dataset，含 quality_status/safety_status 分類
    └── run_checks_demo.py                  # 不需網路：直接驗證 18 條 quality/safety 規則本身
```

未接 Day2/Day6 已建立的 OTel/Prometheus/Loki/Tempo 整套 observability stack，避免重複建置；`metrics.py` 用 `prometheus-client` 直接掛 `/metrics`，`logging_utils.py` 印結構化 JSON 到 stdout，欄位命名與文章一致，方便之後直接接進既有 pipeline。

## 執行方式

```bash
cd Day8/DIY
uv sync

cp .env.example .env
# 填入真實 GEMINI_API_KEY，或留假值只測到「LLM 呼叫失敗」這層

# 1. 不需要網路或真實 Key：驗證 quality/safety 規則本身
uv run python scripts/run_checks_demo.py

# 2. 啟動服務
uv run uvicorn app.main:app --port 8081
curl -s http://127.0.0.1:8081/healthz
curl -s -X POST http://127.0.0.1:8081/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"遠端工作每週最多幾天？"}'
curl -s -L http://127.0.0.1:8081/metrics/

# 3. 跑 golden dataset（需要能連到 LLM 呼叫這一步才有意義）
uv run python scripts/run_golden.py
```

## 實測結果

依 CLAUDE.md 的 DIY SOP，本地元件用假 API Key 測到「連線失敗」這層即可，不需要真 credential。

- [x] `uv sync` 成功解析並安裝所有相依套件（`fastapi` 0.141.1、`google-genai` 2.24.0、`prometheus-client` 0.26.0、`pydantic-settings` 2.15.0 等）
- [x] `uv run python scripts/run_checks_demo.py` **全部 18 條規則通過**——這是本次驗證的核心：Quality Check 1-4（contract 驗證、來源子集檢查、誠實拒答辨識、關鍵事實比對）與 Safety Check 1-3（敏感字詞掃描、tool allowlist 含 fail-closed 預設、高風險過度自信偵測）在不碰網路、不需要真實 LLM 回答的前提下，邏輯本身正確
- [x] `uvicorn` 啟動成功，無 import 或設定錯誤
- [x] `GET /healthz` 回傳 `{"status":"ok"}`
- [x] `POST /ask`（可回答問題與不可回答問題）用假 Key 打到 Gemini，收到 `400 API_KEY_INVALID`，被 `main.py` 的 `except Exception` 正確攔截，回傳 `502 {"detail":"LLM request failed"}`——確認 retrieval、prompt 組裝、request schema 驗證全部跑到 LLM 呼叫這一步才失敗，`evaluation.py` 裡的 quality/safety 分類邏輯因此**未被觸發**（與 Day7 用假 Key 時的失敗邊界一致）
- [x] `GET /metrics/`（注意需要尾隨斜線，`prometheus_client.make_asgi_app()` mount 在 `/metrics` 對 `/metrics` 本身會回 307 到 `/metrics/`）能看到 `ai_response_evaluations_total`、`ai_response_review_required_total`、`ai_unsafe_action_blocked_total` 三個 Counter 已註冊（因為 `/ask` 全部在 LLM 呼叫失敗，尚未累積任何樣本值，屬預期）
- [x] `uv run python scripts/run_golden.py` 對 4 筆 golden dataset 全部正確分類為 `Failed`（假 Key 導致的預期結果），錯誤訊息一致指向 `API_KEY_INVALID`，證明 dataset 載入、四個 async 呼叫並行執行、`evaluate_ask()` 的例外處理與分類邏輯都正確接上
- [x] 測試完清除本地 `.env`，未進 git（`.gitignore` 已排除 `*.env`）

## 發現的問題與修正

1. **文章的 evaluation pipeline 天生無法用假 Key 端到端驗證**：Day8.md 的 Quality/Safety checks 全部運作在「LLM 已經回答」之後（檢查回答內容、引用來源、是否誠實拒答），但假 API Key 會讓流程卡在 Day7 就已存在的 LLM 呼叫這一步。這代表光靠 `run_golden.py` 無法驗證本文新增的邏輯本身是否正確——這正是本次額外寫 `scripts/run_checks_demo.py`（直接對 `quality_checks.py`/`safety_checks.py` 餵合成輸入）的原因：golden dataset 驗證「pipeline 接得起來」，demo script 驗證「規則本身有沒有寫對」，兩者互補，且都不需要真實 LLM 回答就能跑完。

2. **`prometheus_client.make_asgi_app()` 掛在 `/metrics` 時，`GET /metrics`（無尾斜線）會回 307**：這是 Starlette sub-application mount 的標準行為，非本專案 bug，但文章沒有提到，值得記錄避免日後誤判——實際訪問要用 `/metrics/` 或讓 client 自動跟隨 redirect。

3. **`risk_level` 分類是本 DIY 自行補上的簡化設計，文章本身沒有給出程式碼**：Day8.md ⑥ 的 Safety Check 3（高風險不確定性）描述「涉及人事、財務、權限或個資」時要更嚴格判斷，但沒有給出如何判斷問題屬於哪個風險等級的程式碼；Detailed-outline.md 也只給了條件描述，沒有實作。本專案新增 `app/risk.py`，用最粗略的關鍵字表把問題分成 `low`/`high` 兩級（未實作 `medium`，因為關鍵字比對難以可靠分辨「中」與「高」風險），這是本 DIY 為了讓 Safety Check 3 有東西可以跑而做的合理延伸，不是文章原文的一部分，未來若要精確分級應改用真正的分類器或人工維護的規則表。

4. **`sources_are_allowed` 沿用 Day7 的邏輯，但目前的 Prompt/LLM 設計本身不會讓模型「引用」文件**：Day7 的 `build_prompt()` 只是把整份文件塞進 context，並要求模型在回答時 cite document ID，但 `ask_grounded()` 從來沒有解析 LLM 輸出裡的引用字串——`sources` 欄位其實是「Retriever 有取回的文件」，不是「模型真的引用了什麼」。因此 Quality Check 2 目前實質上恆為 `True`（`raw.sources` 與 `raw.retrieved_document_ids` 是同一份資料的兩個欄位）。這個落差在 Day7 就已存在（README 第 3 點已記錄類似問題），Day8 沒有修正它，只是誠實地把這個限制寫下來：要讓 Check 2 真正發揮作用，需要先解析 LLM 回答文字中的引用 ID，這超出本文範圍。

5. **`insufficient_context_handled` 與 `is_high_risk_uncertainty` 都是關鍵字比對，跟文章反覆強調的限制完全一致**：這兩個函式若遇到模型用關鍵字表沒收錄的方式表達「不知道」或「肯定」，就會誤判。這不是本次實作的 bug，而是文章 ①④⑤⑥ 反覆點名的「deterministic checks 只能抓明確、可規則化的風險」——`scripts/run_checks_demo.py` 的測試案例刻意只覆蓋規則設計時預期的措辭，不代表規則能推廣到任意自然語言表達。

## 證據邊界

本次驗證使用假 API Key，能完整證明：`quality_checks.py`/`safety_checks.py` 的 18 條規則邏輯正確、FastAPI 路由與 schema 正確、metrics/log 基礎設施正確掛載、golden dataset 執行框架與例外處理正確。**未驗證**：真實 LLM 回答通過這條 pipeline 之後，`quality_status`/`safety_status` 的分類是否符合預期（例如模型是否真的因為 `insufficient_context_handled` 判定為 `pass`，或是否真的觸發 `scan_sensitive_fields`）。這部分需要真實 `GEMINI_API_KEY`，且如「發現的問題與修正」第 4、5 點所述，即使測了也仍受限於目前 Prompt 設計沒有真正的引用解析，以及關鍵字比對的天生侷限。
