# Day0 DIY — 環境建置 + Gemini Smoke Test

對應 [Day0/Day0.md](../Day0.md) 的實作驗證。獨立 `uv` 專案，不與其他 Day 共用套件環境。

## 內容

```text
Day0/DIY/
├── app/
│   ├── __init__.py
│   └── config.py        # pydantic-settings 讀 .env
├── scripts/
│   └── test_gemini.py   # Gemini Interactions API smoke test
├── .env.example
├── pyproject.toml
└── uv.lock
```

## 執行方式

```bash
cd Day0/DIY
cp .env.example .env   # 填入真正的 GEMINI_API_KEY
uv sync
uv run python scripts/test_gemini.py
```

成功會印出：

```text
Gemini connection OK
```

## 實測結果

- `uv sync`：成功，`google-genai` / `langsmith` / `fastapi` / `pydantic-settings` 皆正常解析安裝。
- `client.interactions.create()`：確認 `google-genai` SDK 目前版本確實有 `client.interactions` namespace，文章描述的新 API 存在。
- 沒有真正的 `GEMINI_API_KEY` 時，執行會在呼叫 Gemini 時得到 `400 API_KEY_INVALID`（預期行為，非程式錯誤）。放入有效 Key 後應可正常回傳 `Gemini connection OK`。

## 發現的問題與修正

1. **文章原始 `uv init` 慣例會產生 `src/<package>/` layout**，但文章要的是 `app/` 這種扁平 layout。直接沿用 `uv init` 預設值不會得到文章裡的目錄結構，需要手動移除 `src/` 並調整 `pyproject.toml`。
2. **`uv run python scripts/test_gemini.py` 預設會 `ModuleNotFoundError: No module named 'app'`**：Python 執行單一腳本時，`sys.path` 只會加入該腳本所在目錄（`scripts/`），不會自動加入 repo 根目錄，因此 `from app.config import get_settings` 找不到 `app`。
   - **修正**：把專案設定為可安裝套件（`pyproject.toml` 加上 `[build-system]` 用 `hatchling`，並在 `[tool.hatch.build.targets.wheel]` 指定 `packages = ["app"]`），讓 `uv sync` 時把 `app/` 安裝進 venv，`import app.config` 就能在任何目錄下work。文章沒有提到這個細節，跟著操作的讀者若照抄很可能會卡在這一步。
3. 其餘步驟（`uv --version`、`uv python install 3.12`、`uv add ...`）皆與文章描述一致，沒有落差。
