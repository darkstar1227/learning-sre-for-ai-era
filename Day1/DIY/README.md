# Day1 DIY — 第一條 AI Workflow Trace

對應 [Day1/Day1.md](../Day1.md) 的實作驗證。獨立 `uv` 專案，與 Day0/Day2 完全分開。

## 內容

```text
Day1/DIY/
├── app/
│   ├── __init__.py
│   ├── config.py     # gemini_api_key + model_name
│   ├── schemas.py     # AskRequest / AskResponse
│   ├── llm.py         # wrap_gemini + @traceable ask_workflow (interactions.create)
│   └── main.py        # FastAPI /healthz /ask
├── .env.example
├── pyproject.toml
└── uv.lock
```

## 執行方式

```bash
cd Day1/DIY
cp .env.example .env   # 填入真正的 GEMINI_API_KEY / LANGSMITH_API_KEY
uv sync
uv run uvicorn app.main:app --reload
```

```bash
curl http://localhost:8000/healthz
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is an SLO?"}'
```

## 實測結果

用假 Key（`fake_test_key`）跑起服務，驗證的是「程式邏輯與資料流本身正不正確」，不是「Gemini 回答正不正確」：

- `GET /healthz` → `200 {"status":"ok"}`，正常。
- `POST /ask` with 空字串 `question` → `422 Unprocessable Entity`，`pydantic` 的 `min_length=1` 驗證確實生效。
- `POST /ask` with 假 Key → Server log 顯示 Gemini 端回 Auth 錯誤，FastAPI 依 `except Exception` 正確包成 `502 Bad Gateway` + `{"detail": "LLM request failed"}`，符合文章設計（不洩漏底層例外細節給 Client）。
- `wrap_gemini()` 與 `@traceable` 皆可正常 import、包裝、執行，沒有版本相容性問題（目前 `langsmith==0.12.2` 仍將 `wrap_gemini` 標為 `LangSmithBetaWarning`，屬預期的 beta 警告，不影響行為）。
- `client.aio.interactions.create()` 在目前安裝的 `google-genai` SDK 上確實存在（`dir(client.aio)` 有 `interactions`），跑同一套假 Key 測試行為正確：乾淨的 `502 Bad Gateway`，不是 code 層級例外。

## 用真實 API Key 補充驗證的細節

1. **可用的 Gemini 模型**：Gemini API 目前對應到 `gemini-3.6-flash`，`app/config.py` 的 `model_name` 預設值以此為準。
2. **`Interaction` 物件取文字的方式**：`google-genai` SDK 的 `Interaction` 物件用 `output_text` 屬性直接取得文字結果，`app/llm.py` 依此讀取。
3. **`wrap_gemini()` 對 Interactions API 的涵蓋範圍**：拿真實 Key 打 `/ask` 並去 LangSmith 後台核對 Run，Trace 樹是 `ask_workflow` → `build_prompt` 兩層；`wrap_gemini()`（`langsmith>=0.12.2`，仍是 Beta）目前主要 instrument 的是 `models.generate_content()` 這條路徑，用 Interactions API（`interactions.create()`）呼叫時不會額外多出一筆 Gemini Run，Gemini 呼叫本身的 Token Usage/Latency 也不在自動記錄範圍內。
4. **`LANGSMITH_PROJECT` 填的是專案名稱，不是後台的識別碼**：填識別碼不會報錯，LangSmith 會直接拿那個值當名稱開一個新專案收 Run，容易讓人以為原本的專案底下 tracing 沒生效。務必填字串名稱（例如 `learning-sre-for-ai-era`）。
5. 其餘部分（FastAPI 專案結構、`app/config.py`、`schemas.py`、`/healthz`、`/ask` 的 502 包裝邏輯）皆與文章描述一致，程式碼可以直接照抄使用（同樣需要注意 Day0 DIY 提到的「`app/` 需設成可安裝套件，否則 `import app.xxx` 會找不到模組」這個 layout 陷阱）。

## 真實 Key 實測結果（LangSmith Run 核對）

用真實 `GEMINI_API_KEY` + `LANGSMITH_API_KEY` 起服務、打 `POST /ask`，回 `200`，正常拿到 Gemini 回答。接著透過 LangSmith `runs/query` API 查詢對應 Project 的 Run，確認：

- `ask_workflow`（`run_type=chain`, `status=success`）確實出現在 LangSmith，是 Root Run。
- `build_prompt`（`run_type=chain`, `status=success`）確實出現，`parent_run_id` 正確指向 `ask_workflow`，Parent/Child 關係如文章描述成立。
- Gemini 呼叫本身沒有獨立 Run，也沒有 Token Usage 欄位（見上方第 3 點）。

結論：LangSmith 確實記錄到這條 Trace，粒度落在 Workflow/Step 這兩層；Gemini Call 這層要看到，需要另外處理（自行記錄，或等 `wrap_gemini()` 支援 Interactions API）。
