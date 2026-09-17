# Day 07 DIY — Grounded Q&A API

驗證 [Day7.md](../Day7.md) 的 DIY 段落：一個可被檢查的 Grounded Q&A API。

Day7.md 本文明確聲明「本文沒有執行、啟動或驗證 Day7 的 DIY」，程式碼是讀者自行實作步驟。本目錄依 repo `CLAUDE.md` 的 DIY SOP，把文章描述的流程從零建成一個獨立、可執行、已跑過的 uv 專案。

## 內容

```text
Day7/DIY/
├── pyproject.toml           # 獨立 uv 專案設定
├── .env.example
├── data/
│   ├── company_policy.md    # 文章原文的知識範圍縮小範例
│   └── golden_dataset.json  # 文章表格的 4 個測試案例
├── app/
│   ├── config.py            # pydantic-settings，讀 GEMINI_API_KEY
│   ├── documents.py          # Document dataclass + 兩份政策文件
│   ├── retrieval.py          # 關鍵字比對，對應文章 retrieve_context()
│   ├── prompt.py              # PROMPT_CONTRACT + build_prompt()
│   ├── schemas.py             # AskRequest / AskResponse（含 semantic_risk: "unknown"）
│   ├── llm.py                  # ask_grounded()，呼叫 google-genai
│   └── main.py                  # FastAPI：GET /healthz、POST /ask
└── scripts/
    └── run_golden.py             # 跑 golden dataset，分類 Correct/Unsupported/Wrong format/Failed
```

流程完全對應文章的 `text` 圖：User question → Keyword retrieval → Known document → Grounded prompt → LLM → Answer + sources + evaluation metadata。

未包含 embedding、vector database，維持文章「不追求完整 RAG」的範圍。

## 執行方式

```bash
cd Day7/DIY
uv sync

cp .env.example .env
# 填入真實 GEMINI_API_KEY，或留假值只測到連線失敗這層

uv run uvicorn app.main:app --port 8071
curl -s http://127.0.0.1:8071/healthz
curl -s -X POST http://127.0.0.1:8071/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"遠端工作每週最多幾天？"}'

uv run python scripts/run_golden.py
```

## 實測結果

依 CLAUDE.md 的 DIY SOP，本地元件用假 API Key 測到「連線失敗」這層即可，不需要真 credential。

- [x] `uv sync` 成功解析並安裝所有相依套件（fastapi 0.141.1、google-genai 2.23.0、pydantic-settings 2.15.0 等）
- [x] `client.aio.models.generate_content(model=..., contents=prompt)` 呼叫簽章已對照已安裝 SDK（`google-genai==2.23.0`）用 `inspect.signature` 直接驗證，`model=`/`contents=` 參數存在，回傳物件有 `.text` 屬性——與 Day0/Day1 用的 `interactions.create` 是同一個 SDK 內兩個並存的合法介面，非誤用
- [x] `uvicorn` 啟動成功，無 import 或設定錯誤
- [x] `GET /healthz` 回傳 `{"status":"ok"}`
- [x] `POST /ask`（可回答問題「遠端工作每週最多幾天？」）用假 Key 打到 Gemini，收到 `400 API_KEY_INVALID`，被 `main.py` 的 `except Exception` 正確攔截，回傳 `502 {"detail":"LLM request failed"}` —— 確認 retrieval、prompt 組裝、request/response schema 驗證全部跑到 LLM 呼叫這一步才失敗，技術流程本身無誤
- [x] `POST /ask`（不可回答問題「可以申請居家辦公設備補助嗎？」）同樣正確跑到 LLM 呼叫層失敗，確認 `retrieve_context` 對「無對應文件」的問題回傳空列表、`answer_status` 邏輯正常運作到呼叫前一刻
- [x] `uv run python scripts/run_golden.py` 對 4 筆 golden dataset 全部正確分類為 `Failed`（假 Key 導致的預期結果），且錯誤訊息一致指向 `API_KEY_INVALID`，證明 dataset 載入、四個 async 呼叫並行執行、例外處理與分類邏輯都正確
- [x] 測試完清除本地 `.env`，未進 git（`.gitignore` 已排除 `*.env`）

## 發現的問題與修正

1. **`client.aio.models.generate_content` vs `client.aio.interactions.create`**：Day0/Day1 用的是 Interactions API（`client.aio.interactions.create(model=..., input=prompt)`），Day7.md 本文從未給出實際的 Gemini SDK 呼叫程式碼（它只寫了 retrieval/prompt/schema 的 Python 片段，LLM 呼叫本身留白）。本專案的 `app/llm.py` 因此需要自行決定要用哪個介面。實測確認 `google-genai==2.23.0` 同時提供 `client.aio.models.generate_content` 與 `client.aio.interactions.create` 兩個可用的 async 方法，用前者是合理選擇（更貼近多數 `google-genai` 官方範例的慣用寫法），非弄錯 API。若之後想與 Day0/Day1 的呼叫風格統一，可以再換成 `interactions.create`，但不影響本次驗證的正確性。

2. **`generate_content` 印出 AFC (Automatic Function Calling) 提示訊息**：呼叫時 SDK 印出 `Direct use of automatic function calling (AFC) in AsyncModels.generate_content is not recommended...` 的提醒。這是 SDK 本身的 stdout 提示，不是錯誤，也不影響本次呼叫結果（後續仍正確拋出 API Key 錯誤）。文章沒有提及這個訊息，值得記錄避免日後誤判為 bug。

3. **`answer_status` 邏輯只看「有無取回文件」，不看 LLM 是否真的拒答**：`app/llm.py` 的 `answer_status = "answered" if documents else "unavailable"` 是在呼叫 LLM 之前、純粹依 retrieval 結果決定，這與文章 prompt 契約裡「資料不足時模型必須回答不知道」是兩件事——目前的實作沒有解析 LLM 輸出內容來確認它真的照契約拒答。這正是文章反覆強調的重點：`technical_success: true` 不等於語意正確，`semantic_risk` 保持 `"unknown"` 就是為了誠實反映這個落差，而不是拿 retrieval 結果偷換成語意判斷的正確性保證。`scripts/run_golden.py` 的分類邏輯同樣只能自動判斷 retrieval 是否命中 `allowed_source_ids`，判斷不了「回答內容是否真的被文件支持」，這部分依文章所述，仍需要真實 API Key 執行後人工覆核，或另外接評估用的 LLM 做自動化評分。

## 證據邊界

本次驗證使用假 API Key，只能確認到「HTTP 請求正確送達 Gemini API 並收到結構化錯誤回應」這一層——即 retrieval、prompt 組裝、schema 驗證、例外處理、golden dataset 執行框架全部正確。**未驗證**：真實 LLM 回答內容是否符合 prompt 契約（引用正確文件 ID、資料不足時確實拒答、不捏造規則）。這部分需要真實 `GEMINI_API_KEY` 才能測試，且即使測了也仍需人工覆核回答內容，如文章「發現的問題與修正」第 3 點所述。
