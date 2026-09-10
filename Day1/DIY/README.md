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

## 發現的問題

1. `wrap_gemini()` 目前主要 instrument 的對象是 `models.generate_content`；用 `interactions.create()` 後 tracing 是否仍完整記錄 token usage/latency 等欄位，需要用真實 API Key 實測 LangSmith 上的 Run 內容才能確認（本次僅用假 Key 驗證到「呼叫路徑正確、失敗方式正確」這層，尚未驗證 trace 內容本身）。
2. 其餘部分（FastAPI 專案結構、`app/config.py`、`schemas.py`、`/healthz`、`/ask` 的 502 包裝邏輯）皆與文章描述一致，程式碼可以直接照抄使用（同樣需要注意 Day0 DIY 提到的「`app/` 需設成可安裝套件，否則 `import app.xxx` 會找不到模組」這個 layout 陷阱）。
