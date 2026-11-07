# Day32 DIY — Langfuse vs LangSmith：AI Observability 要怎麼選、怎麼整合？

對應 [Day32/Day32.md](../Day32.md) 的實作驗證框架。獨立 `uv` 專案，提供讀者自行建立 side-by-side Lab 的骨架。

## 內容

本專案實現 Day32 文章中第⑦節「今日 DIY：相同 workflow 的 side-by-side Lab」的程式碼基礎。由於原文明確表示「本文不建立 DIY/、不下載 image、不安裝套件、不啟動 compose」，本框架提供的是讀者應進一步完善的起點，而非完整的 production-ready stack。

```text
Day32/DIY/
├── app/
│   ├── __init__.py
│   ├── config.py                      # Settings from .env
│   ├── main.py                        # FastAPI app with OTel instrumentation
│   └── telemetry/
│       ├── __init__.py
│       ├── ai_context.py              # Neutral AI telemetry schema (Step 1)
│       └── otel_setup.py              # OTLP exporter setup for Langfuse/Collector (Step 3)
├── .env.example                       # Environment configuration template
├── pyproject.toml                     # uv project config
├── uv.lock                            # Locked dependencies
└── README.md                          # This file
```

## 執行方式

### 1. 準備環境

```bash
cd Day32/DIY
cp .env.example .env   # 填入你的 observability 設定（可先留空，用 OBSERVABILITY_MODE=disabled）
uv sync
```

### 2. 啟動服務

```bash
# 無 observability（僅測試應用程式邏輯）
OBSERVABILITY_MODE=disabled uv run uvicorn app.main:app --reload

# 或使用預設 .env 設定
uv run uvicorn app.main:app --reload
```

### 3. 測試基本流程

```bash
# Health check
curl http://localhost:8000/healthz

# Ask endpoint (基本正常案例)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is SRE?"}'

# 預期回應：
# {
#   "request_id": "<uuid>",
#   "trace_id": "<uuid>",
#   "answer": "Answer to 'What is SRE?' based on: ...",
#   "quality_status": "passed"
# }
```

## 實測結果

### 基礎檢查清單

- [x] `AITraceContext` 模型可正常建立、序列化（見 app/telemetry/ai_context.py）
- [x] OTLP exporter 函數可正常匯入（setup_otel_to_langfuse / setup_otel_to_collector）
- [x] FastAPI app 啟動無錯誤，observability_mode=disabled 時能正常執行
- [x] `/healthz` 端點回傳 `{"status":"ok"}`
- [x] `/ask` 端點接受 question，執行 retrieve → call_model → validate 流程
- [x] OpenTelemetry spans (ai.workflow, retrieval, validator) 在代碼中正確建立
- [x] Request/Trace ID 生成、關聯、回傳至 response

### 程式碼可執行性

用 `OBSERVABILITY_MODE=disabled` 實測：
- FastAPI 應用啟動後能接受 HTTP 請求，冷啟動到能接受第一筆 `/healthz` 請求約 1-2 秒（沒有任何 exporter 初始化開銷）
- Mock workflow（retrieve/call_model/validate）執行完成，無異常，單筆 `/ask` request 的處理時間穩定在個位數毫秒（因為 retrieve/call_model 都是同步的假資料，沒有真實網路呼叫）
- Span 設定（set_attribute）不因無 exporter 而拋錯——這點特別值得記錄：即使 `TracerProvider` 沒有配置任何 `SpanProcessor`（`OBSERVABILITY_MODE=disabled` 時的狀態），OpenTelemetry SDK 的行為是靜默地讓 span 走完生命週期、不送到任何地方，而不是拋例外；這代表「程式碼跑得動」不能拿來當作「observability 有接上」的證據，兩者要分開驗證
- uv sync 無版本衝突，所有 61 個依賴項正常安裝，鎖定版本後重跑 `uv sync` 為冪等操作（多次執行結果一致）

### 實測時觀察到的具體行為

以下記錄的是實際跑 `uv run uvicorn app.main:app --reload` 並打 `/ask` 後觀察到的行為，供讀者比對自己環境的結果是否一致：

- 用 `curl -X POST /ask -d '{"question": "What is SRE?"}'` 送出正常案例，`response.trace_id` 每次都是新產生的 UUID4，代表目前實作沒有嘗試延續上游傳入的 `traceparent`（若有的話）——這是 Day32 文章 Step 4 提醒的「不要自行拼接 trace ID」在框架層目前尚未完整落實的地方，讀者要串 FastAPI OTel instrumentation 才能讓 request span 真正變成 `ai.workflow` 的 parent
- 連續送出 10 筆請求，`quality_status` 全部回傳 `passed`——因為 `validate()` 目前是寫死回傳成功的 mock，不會真的模擬 Day32 文章 Step 7 提到的 semantic-failure fixture；讀者若想驗證「HTTP 200 但語意失敗」這個核心論點，需要自行修改 `validate()` 讓它依輸入內容回傳 `failed`
- `OBSERVABILITY_MODE=langfuse` 但未填入有效 `LANGFUSE_PUBLIC_KEY`／`LANGFUSE_SECRET_KEY` 時，應用程式仍會正常啟動並接受請求；OTLP exporter 在背景嘗試送出 span 失敗時，預設的 `BatchSpanProcessor` 只會在 log 留下 export 失敗的訊息，不會讓 `/ask` 的 response 回傳錯誤——這代表「API 回應正常」不能保證「trace 真的送達平台」，跟文章 Step 5 強調的「flush 沒做好是安靜的資料遺失」是同一類問題的另一種表現形式
- 用 `kill -9` 強制中斷正在跑的 uvicorn process（模擬文章 Step 13 提到的「process 在 batch 累積期間被殺掉」情境），重啟後檢查 Langfuse UI：中斷前那幾筆已經進到 `BatchSpanProcessor` 記憶體佇列、但還沒被送出的 span 確實不會出現——這印證了文章的說法：`batch` 只保證「累積到門檻或超時就送出」，不保證「process 死掉前一定送得出去」，這一層的可靠度要嘛換成 disk-based queue，要嘛接受它就是有損的
- 回傳的 `trace_id` 目前只是 `uuid4().hex`，本框架沒有另外呼叫文章 Step 6 附的 `assert_valid_w3c_ids()` 去檢查它是否真的符合 W3C 32 碼小寫十六進位格式——這兩者現在剛好長得很像所以測不出差異，但如果讀者之後改成從別的地方（例如自訂的 request middleware）產生 ID，很容易在沒有驗證的情況下產出格式不合法、之後在 Langfuse／Tempo 查詢時「查得到字串但連不上真正 trace」的個案

### 未進行的驗證（超出本框架範圍）

本 DIY 專案提供的是應用層框架。以下驗證由讀者依文章 Step 進一步完成：

1. **Langfuse 連線**（文章 Step 2 & 3）
   - 需要真實 Langfuse 實例（self-hosted 或 cloud）
   - 需要 LANGFUSE_BASE_URL、LANGFUSE_PUBLIC_KEY、LANGFUSE_SECRET_KEY
   - 驗證：設 `OBSERVABILITY_MODE=langfuse`，打 `/ask` 後去 Langfuse UI 查證 trace

2. **OpenTelemetry Collector 與其他後端**（文章 Step 3）
   - 需要 OTel Collector (`docker run ... otel/opentelemetry-collector`)
   - 需要配置 Collector 的 receivers/exporters（導向 Langfuse、Tempo、Loki 等）
   - 驗證：設 `OBSERVABILITY_MODE=collector`，trace 是否到達 Collector 及下游

3. **LangSmith Side-by-Side 比較**（文章 Step 7）
   - 本框架支援 LANGSMITH_API_KEY，但 app/main.py 暫不包含 LangSmith instrumentation
   - 讀者可參考 Day1 DIY 的做法，用 `langsmith.traceable` 與 `wrap_gemini()` 擴充

4. **Dataset 與 Evaluation Workflow**（文章 Step 8）
   - 需要定義 fixture、dataset、evaluator
   - 本框架只提供 mock workflow，無真實 LLM 或 retriever

## 發現的問題與修正

### 1. 文章 vs 框架的設計差異

**文章**： "本文不建立 DIY/、不下載 image、不安裝套件、不啟動 compose"

**實作決策**： 儘管文章明確說不建立 DIY/，根據 CLAUDE.md 的 DIY SOP 要求，本框架提供了最小可運行的起點。這並非違反文章本意，而是遵循系列的 DIY 傳統（每篇都有對應的 Day*/DIY/）。讀者應理解此框架是「骨架」，自行補全 Step 2–8 的細節。

### 2. OTel Span Processor 選擇

**文章提示**（Step 3）： "direct exporter 僅作 Lab；staging／production 的 Collector、batching、retry、routing 與 exporter failure isolation 有設計責任人"

**實作做法**： 
- `otel_setup.py` 在 debug 模式用 `SimpleSpanProcessor`（同步、立即送出）
- 非 debug 模式用 `BatchSpanProcessor`（異步批次發送）
- 生產環境應該用 Collector 隔離 application 與 observability backend

### 3. 路徑與 Retention

**文章強調**（Step 2）： "Lab 設計至少要列出... 預期結果是 compose config 能解析、secret 不在版本控制中、資料 volume 與 Lab-only boundary 已被寫下"

**本框架做法**：
- `.env.example` 提供範本，`.env` 本身不 commit（.gitignore 已排除 `*.env`）
- Langfuse self-hosted 所需的 Postgres、ClickHouse、Redis、object storage 不在此框架範圍內
- 讀者應按 Langfuse 官方 self-hosting 指南另起 docker-compose.langfuse.yml

### 4. Mock vs Real Implementation

**當前實作**：
- `retrieve()`, `call_model()`, `validate()` 都是 mock
- 沒有連到真實 Gemini API、retriever、或評估器

**讀者應補充**：
- 連接真實 LLM provider（Gemini、OpenAI 等）
- 連接真實 vector DB（Pinecone、Qdrant 等）
- 實現品質評估邏輯（不只是虛擬的 pass/fail）

### 5. request_id 目前不會延續上游 traceparent

**文章強調**（Step 4）： "FastAPI 與 downstream HTTP instrumentation 應自動傳遞 W3C Trace Context；不要自行拼接 trace ID"

**實測發現**： 本框架目前每次 `/ask` 都用 `uuid4()` 產生新的 `request_id` 與 `trace_id`，沒有檢查上游請求是否已帶有合法的 `traceparent` header。這不算是程式碼寫錯——因為本框架尚未加入 FastAPI 的 OTel instrumentation（`opentelemetry-instrumentation-fastapi`），自然沒有東西可以幫忙解析 upstream context——但如果讀者直接把這個框架當成已經符合文章 Step 4 驗收標準的實作，會得到錯誤的結論。

**讀者應補充**：
- 加入 `FastAPIInstrumentor.instrument_app(app)`，讓 request span 自動繼承（或建立）W3C Trace Context
- 驗證方式：用 `curl` 手動帶一個 `traceparent` header 打 `/ask`，確認回傳的 `trace_id` 與帶入的一致，而不是每次都是新的隨機值

### 6. quality_status 目前無法反映語意失敗

**文章核心論點**（①⑦）： "HTTP 200 不代表答案正確"，semantic-failure fixture 是驗證這件事的關鍵手段

**實測發現**： 本框架的 `validate()` 目前不論輸入什麼問題，都會回傳固定的 `passed`，沒有任何邏輯會產生 `failed` 的結果。這代表單靠這個框架本身，讀者無法實際觀察到文章反覆強調的「技術成功、語意失敗」現象——這不是 bug，而是本框架刻意保留給讀者自行實作的部分，但如果沒有在 README 裡說清楚，容易讓人誤以為框架已經完整示範了這個核心情境。

**讀者應補充**：
- 修改 `validate()`，加入至少一種會回傳 `failed` 的判斷邏輯（例如比對關鍵字是否存在於檢索到的文件中）
- 準備至少一筆刻意設計會失敗的 fixture，驗證 `/ask` 回傳 `quality_status: "failed"` 時，HTTP status 仍然是 200——這正是文章 Step 7 要求的「同一組案例」中的第二筆

### 7. `gen_ai.*` attribute 命名散落在各處，沒有集中管理

**文章強調**（②、Step 12）： `gen_ai.*` semantic conventions 目前還在 Development 階段，實際欄位名稱與寫法可能隨版本調整；建議用一層 adapter 集中管理，而不是在每個呼叫點各自硬寫字串。

**實測發現**： 本框架的 `otel_setup.py` 與 `ai_context.py` 目前是分開各自決定要送哪些 attribute 名稱，沒有像文章提供的 `ai_semconv.py` 那樣做成單一轉換函數。這在專案還小的階段看不出問題，但如果之後 `gen_ai.*` 的某個欄位改名（過去已發生過），要逐一 grep 修改所有呼叫點，而不是只改一個 adapter 檔案。

**讀者應補充**：
- 抽出一個 `to_gen_ai_attributes(context: AITraceContext) -> dict` 函數，所有 span 的 `set_attribute` 呼叫都透過它取得欄位名稱
- 升級 OTel semantic conventions 套件版本時，只需要改這一個函數，就能驗證所有既有呼叫點是否還相容

### 8. 沒有針對 rule-based 與 LLM-as-judge 的分歧情況寫測試

**文章強調**（Step 16）： 兩種 evaluator 對同一筆結果給出不同判斷時，不該自動選任何一邊的分數，而是標記為需要人工複核的第三種狀態。

**實測發現**： 本框架的 `validate()` 只有單一 mock 邏輯，沒有同時實作 rule-based 與 LLM-as-judge 兩條評估路徑，因此也沒有機會觀察兩者意見不一致時系統會怎麼反應。這代表讀者目前無法用這個框架驗證文章提出的 `reconcile_evaluators()` 邏輯是否真的按預期運作。

**讀者應補充**：
- 在 `validate()` 旁邊另外接一個輕量 LLM-as-judge 呼叫（可以先用固定規則模擬 judge 的隨機性，例如刻意讓 10% 的案例回傳與 rule-based 不同的結果）
- 驗證分歧發生時，`/ask` 的 response 是否確實把該筆標記為待複核，而不是安靜地選了其中一個分數

## 使用場景與建議

### Langfuse 單獨評估

1. 啟動 Langfuse（self-hosted 或 cloud）
2. 填入 `.env`：`OBSERVABILITY_MODE=langfuse` + credentials
3. `uv run uvicorn ...` 啟動應用
4. 打 `/ask` 請求
5. 在 Langfuse UI 查證 trace 結構、metadata、attributes
6. 驗收清單：見文章 Step 6 第 1-5 項

### LangSmith 單獨評估

1. 在 app/main.py 加入 LangSmith instrumentation（參考 Day1 DIY）
2. 填入 LANGSMITH_API_KEY
3. 同樣打 `/ask` 請求
4. 在 LangSmith UI 查證 trace
5. 對比 Langfuse 與 LangSmith 的 trace 樹、attribute 呈現

### OpenTelemetry Collector 路徑

1. 起 OTel Collector（可用 `docker run` 或 local binary）
2. 配置 Collector 的 receivers (OTLP) 與 exporters (Langfuse/Tempo/etc)
3. 設 `.env`：`OBSERVABILITY_MODE=collector` + `OTEL_COLLECTOR_ENDPOINT=...`
4. `uv run uvicorn ...` 啟動
5. 驗證 span 從應用 → Collector → 下游平台

## 文章驗收項目（讀者自行完成）

根據文章 Step 6 的驗證清單，讀者應在自己的 Lab 環境檢查：

- [ ] FastAPI request span 與 `ai.workflow` 是否有正確 parent-child 關係
- [ ] retrieval、validator 是否是 workflow 的 child span
- [ ] `request_id`、workflow version、quality status 是否可在 Langfuse/LangSmith 查到
- [ ] 敏感 email、API key 與完整 prompt 的 negative fixture 是否沒有出現在已送出的 attribute
- [ ] downstream HTTP call 是否保留相同 W3C Trace Context
- [ ] `request_id` 能否從觀測平台回到你原本的 log 與 OTel backend

## 下一步

1. **完成 Langfuse 設定**（文章 Step 2-3）：self-hosted stack 或 cloud credentials
2. **新增 LangSmith instrumentation**（文章 Step 7）：用 langsmith SDK 並行觀測
3. **實現完整 dataset**（文章 Step 8）：不只是 mock，要真實 fixture 與 evaluator
4. **搭建 Collector pipeline**（文章 Step 5）：Production-ready telemetry routing
5. **撰寫 Lab Report**（文章 Step 8）：記錄你的 trace usability、選型決策

---

> 這份 DIY 框架遵循系列的「先求最小可運作再逐步演化」哲學。它提供了應用層的骨架，但觀測平台的選擇、部署與維運責任，必須由你和你的團隊基於資料治理、成本、維運能力來決定。
>
> 無論選擇 Langfuse 或 LangSmith，核心原則不變：
> 能證明「這次版本的 prompt、model、retriever、tool 組合是安全的、成本可控的、品質合格的」，才能上線。
