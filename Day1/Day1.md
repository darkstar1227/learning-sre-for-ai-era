# Day 01--用 LLM Trace 看見一次 AI Workflow 的完整生命週期

**Using LLM Tracing to See Inside an AI Workflow**

如果一個 API 回傳：

```text
HTTP/1.1 200 OK
```

代表系統成功了嗎？

在傳統 Web Service 裡，我們至少可以說：

> 這次 HTTP Request 成功完成了。

但如果 API 背後站著的是 LLM，事情就沒這麼簡單。

假設公司做了一個內部 HR Assistant。

使用者問：

```text
公司請假規則是什麼？
```

API 回傳：

```text
HTTP/1.1 200 OK
```

LLM 回答：

```text
員工每年享有 30 天特休。
```

乍看一切正常。

唯一的問題是：

**公司的規章裡根本沒有這一條。**

恭喜。

API 成功了，使用者任務卻失敗了。

---

# ① HTTP 200 真的代表 AI 系統成功嗎？

如果我們只從傳統 Web Service 的角度觀察這個系統，可能會看到：

```text
Status Code: 200
Latency: 1.8s
CPU: 23%
Memory: 41%
Error Rate: 0%
```

Dashboard 一片綠。

值班工程師甚至可以放心去泡咖啡。

但我們仍然不知道：

- LLM 實際收到什麼 Prompt？
- 呼叫的是哪個 Model？
- Model Call 花多久？
- Input 有多少 Token？
- Output 有多少 Token？
- 有沒有 Retry？
- 最後模型到底產生什麼答案？
- 如果答案錯了，是 Prompt、Model、Retriever、Tool 還是 Parser？

這就是 AI Application 開始與一般 API 分岔的地方。

> **HTTP 200 只能代表技術請求成功，不代表使用者任務成功。**

所以 Day 1 我不打算先塞給你：

- Prometheus
- Grafana
- SLI
- SLO
- Error Budget
- Kubernetes

今天只做一件事：

> **打開一次 LLM Request，看看它的完整生命週期。**

---

# ② 先從傳統 Distributed Tracing 開始

一個傳統服務可能長這樣：

```text
Client
  ↓
API
  ↓
Application
  ↓
Database
  ↓
Response
```

如果這次 Request 很慢，Distributed Tracing 可以把整段 Request 拆開：

```text
HTTP Request                         820 ms
├── Authentication                   20 ms
├── Application Logic               100 ms
└── PostgreSQL Query                700 ms
```

這時候問題一眼就很明顯：

> FastAPI 沒有拖時間，真正卡住的是 PostgreSQL。

Trace 的價值，就是把原本的一個：

```text
Request
```

拆成：

```text
Request
├── Step A
├── Step B
└── Step C
```

讓我們知道：

- Request 走過哪些地方
- 每一步花多少時間
- 哪一步失敗
- Failure 發生在哪個 Dependency

這些資訊讓 Failure Domain 更快縮小，Reliability Engineering 不必靠猜。

---

# ③ 當 Request 裡面開始出現 LLM

當 Application 加入 LLM 後，一條 Request 可能逐漸變成：

```text
Client
  ↓
API
  ↓
Prompt Construction
  ↓
Retriever
  ↓
LLM
  ↓
Tool Call
  ↓
Output Parser
  ↓
Safety Validation
  ↓
Response
```

這條路徑早已超過傳統的：

```text
API → Database → Response
```

它是一條：

# AI Workflow

未來一個 AI Application 可能包含：

```text
Prompt
Retriever
Vector DB
Embedding Model
LLM Provider
Tools
Parser
Guardrails
Evaluator
```

每一個步驟都可能：

- 變慢
- Timeout
- Retry
- 回傳錯誤
- 消耗成本
- 產生錯誤結果

但 Day 1 我們先不要搞這麼大。

今天只建立最小 Workflow：

```text
Client
  ↓
FastAPI
  ↓
Prompt
  ↓
Gemini
  ↓
Response
```

沒有：

- RAG
- Agent
- Tool Calling
- Vector Database
- Guardrails
- Multi-model Routing
- GPU Inference
- Evaluation Pipeline

第一天如果全部塞進來，我們最後最熟的東西可能不是 SRE。

而是：

```bash
docker compose down
```

---

# ④ Metrics、Logs、Traces 分別回答什麼？

在正式進入 LLM Trace 之前，先建立最基本的 Observability 直覺。

| Telemetry | 最擅長回答                  |
| --------- | --------------------------- |
| Metrics   | 整體系統現在好不好？        |
| Logs      | 某件事情實際發生了什麼？    |
| Traces    | 這次 Request 經過哪些步驟？ |
| LLM Trace | 這次 AI Workflow 怎麼執行？ |

假設 Production 突然出現：

```text
P95 Latency

1.8s → 12.4s
```

Metrics 可以告訴我們：

> 系統變慢了。

但接下來的問題是：

> **哪裡慢？**

Logs 可能看到：

```text
Gemini request timeout
```

我們開始有方向了。

Trace 則可能直接看到：

```text
POST /ask                     12.4s
└── ask_workflow              12.2s
    ├── build_prompt            2ms
    └── Gemini                12.1s
```

這時候至少不用召集五個人開始通靈：

> 「是不是 FastAPI async 寫壞了？」

不是。

證據就在眼前。

---

# ⑤ 所以什麼是 LLM Trace？

LLM Trace 沒有另開一套 Observability 世界。

比較好的理解方式是：

> **LLM Tracing 是 Distributed Tracing 往 AI Workflow 內部延伸。**

傳統 Trace 關心：

```text
Frontend
  ↓
Backend
  ↓
Database
```

LLM Application 還會多觀察：

```text
Prompt
  ↓
Retrieval
  ↓
Model
  ↓
Tool
  ↓
Parser
```

於是除了傳統的：

- Latency
- Error
- Dependency

之外，我們還會開始追蹤：

- Prompt
- Model
- Token Usage
- Retry
- Tool Calls
- Retrieved Documents
- Cost
- Evaluation Result

> **LLM Trace 用來理解 AI Workflow 的執行路徑，不是偷看模型回答。**

---

# ⑥ LangSmith 在整個 Workflow 的哪裡？

第一次看到：

```python
client = wrappers.wrap_gemini(
    gemini_client,
)
```

很容易誤解成：

> LangSmith 是不是變成 Gemini 前面的一層 Proxy？

不是。

實際關係比較接近：

```text
                     ┌─────────────────────────┐
                     │       LangSmith         │
                     │                         │
                     │ Trace / Run / Metadata  │
                     └────────────▲────────────┘
                                  │
                                  │ Telemetry
                                  │
Client                            │
  │                               │
  ▼                               │
FastAPI                           │
  │                               │
  ▼                               │
ask_workflow ─────────────────────┤
  │                               │
  ▼                               │
build_prompt ─────────────────────┤
  │                               │
  ▼                               │
wrap_gemini() ────────────────────┤
  │
  ▼
Google Gen AI SDK
  │
  │ HTTPS Request
  ▼
Gemini API
  │
  ▼
LLM Response
  │
  ▼
FastAPI
  │
  ▼
Client
```

真正負責呼叫 Gemini 的仍然是：

```text
Google Gen AI SDK
```

LangSmith 的角色比較接近：

```text
Instrumentation
       +
Trace Backend
```

也就是：

> **Application 照常執行 Gemini Call，同時把這次執行產生的 Telemetry 記錄下來。**

---

## 這裡有兩條資料流

### 業務請求路徑

```text
Client
 ↓
FastAPI
 ↓
Google Gen AI SDK
 ↓
Gemini API
 ↓
Response
```

這條路徑負責真正服務使用者。

### Observability 路徑

```text
Application
 ↓
LangSmith Instrumentation
 ↓
Trace / Run
 ↓
LangSmith
```

這條路徑負責回答：

> 剛剛那次 Workflow 到底發生了什麼？

這兩條路徑不要混在一起。

---

# ⑦ `wrap_gemini()` 到底在做什麼？

原本我們可能直接建立 Gemini Client：

```python
gemini_client = genai.Client(
    api_key=settings.gemini_api_key,
)
```

然後：

```python
response = await gemini_client.aio.interactions.create(
    model=settings.model_name,
    input=prompt,
)
```

概念上：

```text
Application
 ↓
Google Gen AI SDK
 ↓
Gemini
```

加入：

```python
client = wrappers.wrap_gemini(
    gemini_client,
)
```

後，可以把它理解成：

```text
Gemini Call 開始
 ↓
記錄 Start Time
 ↓
記錄 Input / Model
 ↓
真正送出 Gemini Request
 ↓
收到 Gemini Response
 ↓
記錄 Output
 ↓
記錄 Token Usage
 ↓
計算 Latency
 ↓
如果失敗，記錄 Error
 ↓
結束 Run
```

因此：

```python
client.aio.interactions.create(...)
```

功能上仍然是在：

> 呼叫 Gemini。

只是同時多了一份：

```text
Telemetry
```

---

# ⑧ `@traceable` 又是在做什麼？

`wrap_gemini()` 能知道：

> 這裡發生了一次 Gemini Call。

但 Application 不只有 Gemini Call。

例如：

```python
@traceable(
    name="build_prompt",
    run_type="chain",
)
def build_prompt(question: str) -> str:
    ...
```

代表：

> `build_prompt()` 是 Workflow 裡的一個可觀測步驟。

再例如：

```python
@traceable(
    name="ask_workflow",
    run_type="chain",
)
async def ask_llm(question: str):
    ...
```

代表：

> 整個 `ask_llm()` 是更上層的 Workflow。

所以我們最後不是得到：

```text
ask_workflow
build_prompt
Gemini
```

三筆互不相關的紀錄。

而是：

```text
ask_workflow
│
├── build_prompt
│
└── Gemini
```

形成 Parent / Child 關係。

---

# Trace、Run、Span 可以怎麼理解？

如果你有 Distributed Tracing 經驗，可以暫時這樣對照：

```text
LangSmith Trace
≈
Distributed Trace

LangSmith Run
≈
Span
```

例如：

```text
Trace: Request #A123

ask_workflow                   1.8s
│
├── build_prompt               2ms
│
└── Gemini Call               1.7s
```

整體是一條：

```text
Trace
```

裡面的：

```text
ask_workflow
build_prompt
Gemini Call
```

是不同的：

```text
Run
```

而且 Runs 之間有：

```text
Parent
  ↓
Child
```

的關係。

這就是為什麼我們可以知道：

> Gemini 的 1.7 秒，屬於哪一次 `/ask` Request。

而不是只有一條孤零零的：

```text
Gemini latency = 1.7s
```

---

# ⑨ 一次 LLM Request 實際發生了什麼？

把整條 Request 拆開：

```text
① Client 發送 POST /ask

        ↓

② FastAPI 收到 Question

        ↓

③ ask_workflow 開始
   建立 Parent Run

        ↓

④ build_prompt 執行
   建立 Child Run

        ↓

⑤ Application 呼叫 Gemini

        ↓

⑥ wrap_gemini Instrument SDK Call
   建立 Gemini Run

        ↓

⑦ Google Gen AI SDK
   將 HTTPS Request 送到 Gemini API

        ↓

⑧ Gemini 產生 Response

        ↓

⑨ SDK 收到 Response

        ↓

⑩ LangSmith 記錄
   - Input
   - Output
   - Model
   - Latency
   - Token Usage
   - Error

        ↓

⑪ ask_workflow 結束

        ↓

⑫ FastAPI 回傳 JSON
```

最後 LangSmith UI 就可以將它重建成：

```text
POST /ask
└── ask_workflow
    ├── build_prompt
    └── Gemini
```

---

# ⑩ SRE Lab：建立第一個 AI Service

今天要完成的架構很小：

```text
POST /ask
  ↓
FastAPI
  ↓
Build Prompt
  ↓
Call Gemini
  ↓
LangSmith Trace
  ↓
JSON Response
```

使用：

```text
FastAPI
Google Gen AI SDK
Gemini API
LangSmith
uv
```

專案結構：

```text
day01-ai-trace/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── llm.py
│   ├── main.py
│   └── schemas.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── uv.lock
```

Day 0 已經處理過 Python、uv、Gemini API Key 與 LangSmith API Key，Day 1 直接開始建立服務。

---

## Step 1：加入 Dependencies

如果 Day 0 還沒裝完整，可以執行：

```bash
uv add \
  fastapi \
  "uvicorn[standard]" \
  google-genai \
  langsmith \
  pydantic-settings
```

確認：

```bash
uv sync
```

---

## Step 2：準備環境變數

`.env`：

```text
GEMINI_API_KEY=your_gemini_api_key

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=learning-sre-ai-era-day01

MODEL_NAME=gemini-2.5-flash
```

其中：

```text
GEMINI_API_KEY
```

負責：

```text
Application → Gemini
```

而：

```text
LANGSMITH_API_KEY
```

負責：

```text
Application → LangSmith
```

這正好對應前面那兩條不同資料流。

---

## Step 3：建立 Application Settings

建立：

```text
app/config.py
```

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str
    model_name: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

這裡只管理 Application 自己需要讀取的：

```text
GEMINI_API_KEY
MODEL_NAME
```

LangSmith 則直接讀 Environment Variables。

---

## Step 4：建立 API Schema

`app/schemas.py`：

```python
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
    )


class AskResponse(BaseModel):
    answer: str
    model: str
```

我們的 API 很單純。

Request：

```json
{
  "question": "What is an SLO?"
}
```

Response：

```json
{
  "answer": "An SLO is ...",
  "model": "gemini-2.5-flash"
}
```

這是故意的。

Day 1 要看的不是 API Architecture。

而是：

```text
Request 裡面發生了什麼？
```

---

## Step 5：建立 Gemini Client

建立：

```text
app/llm.py
```

先初始化 Gemini：

```python
from google import genai
from langsmith import traceable, wrappers

from app.config import get_settings


settings = get_settings()

gemini_client = genai.Client(
    api_key=settings.gemini_api_key,
)
```

再交給 LangSmith instrumentation：

```python
client = wrappers.wrap_gemini(
    gemini_client,
    tracing_extra={
        "tags": [
            "day01",
            "gemini",
        ],
        "metadata": {
            "provider": "google",
            "sdk": "google-genai",
        },
    },
)
```

現在：

```text
Application
 ↓
wrap_gemini
 ↓
Google Gen AI SDK
 ↓
Gemini
```

但記得：

> `wrap_gemini()` 不是 LLM Provider，也不是 Reverse Proxy。

---

# Step 6：建立 Prompt Step

接著定義一個最小 Prompt：

```python
SYSTEM_PROMPT = """
You are a concise SRE tutor.

Answer the user's question accurately and briefly.

If you are unsure, clearly state what is uncertain
instead of inventing information.
"""
```

再建立 Prompt function：

```python
@traceable(
    name="build_prompt",
    run_type="chain",
)
def build_prompt(
    question: str,
) -> str:

    return f"""
{SYSTEM_PROMPT}

User question:
{question}
""".strip()
```

但我們故意讓它：

```text
Traceable
```

因為未來 Prompt Construction 可能開始包含：

```text
System Prompt
User Context
Retrieved Documents
Policy
Prompt Version
```

Day 1 先把這個 Workflow Boundary 留出來。

---

## Step 7：建立完整 AI Workflow

接著：

```python
@traceable(
    name="ask_workflow",
    run_type="chain",
)
async def ask_llm(
    question: str,
) -> dict[str, str]:

    prompt = build_prompt(question)

    interaction = await client.aio.interactions.create(
        model=settings.model_name,
        input=prompt,
    )

    return {
        "answer": interaction.outputs[-1].text or "",
        "model": settings.model_name,
    }
```

完整的 `app/llm.py`：

```python
from google import genai
from langsmith import traceable, wrappers

from app.config import get_settings


settings = get_settings()

gemini_client = genai.Client(
    api_key=settings.gemini_api_key,
)

client = wrappers.wrap_gemini(
    gemini_client,
    tracing_extra={
        "tags": [
            "day01",
            "gemini",
        ],
        "metadata": {
            "provider": "google",
            "sdk": "google-genai",
        },
    },
)


SYSTEM_PROMPT = """
You are a concise SRE tutor.

Answer the user's question accurately and briefly.

If you are unsure, clearly state what is uncertain
instead of inventing information.
"""


@traceable(
    name="build_prompt",
    run_type="chain",
)
def build_prompt(
    question: str,
) -> str:

    return f"""
{SYSTEM_PROMPT}

User question:
{question}
""".strip()


@traceable(
    name="ask_workflow",
    run_type="chain",
)
async def ask_llm(
    question: str,
) -> dict[str, str]:

    prompt = build_prompt(question)

    interaction = await client.aio.interactions.create(
        model=settings.model_name,
        input=prompt,
    )

    return {
        "answer": interaction.outputs[-1].text or "",
        "model": settings.model_name,
    }
```

現在我們已經得到：

```text
ask_workflow
│
├── build_prompt
│
└── Gemini
```

`ask_workflow` 現在已經串起 `build_prompt` 與 Gemini Call。

---

## Step 8：建立 FastAPI Endpoint

建立：

```text
app/main.py
```

```python
from fastapi import FastAPI, HTTPException

from app.llm import ask_llm
from app.schemas import AskRequest, AskResponse


app = FastAPI(
    title="Learning SRE for the AI Era — Day 01",
    version="0.1.0",
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.post(
    "/ask",
    response_model=AskResponse,
)
async def ask(
    request: AskRequest,
) -> AskResponse:

    try:
        result = await ask_llm(
            request.question,
        )

        return AskResponse(**result)

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="LLM request failed",
        ) from exc
```

目前沒有：

```text
ProviderAdapter
ModelRouter
LLMFactory
PromptRepository
WorkflowManager
```

因為我們現在只有：

```text
FastAPI → Gemini
```

如果第一天就生出：

```text
AbstractAIProviderFactoryManager
```

那不是 Architecture。

那是創傷。

---

## Step 9：啟動服務

執行：

```bash
uv run uvicorn app.main:app --reload
```

先測試：

```bash
curl http://localhost:8000/healthz
```

應該得到：

```json
{
  "status": "ok"
}
```

接著送出第一個 AI Request：

```bash
curl \
  -X POST \
  http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is an SLO?"
  }'
```

可能得到：

```json
{
  "answer": "An SLO is a target level of reliability for a service.",
  "model": "gemini-2.5-flash"
}
```

指令列測試成功；接下來要看的，是 LangSmith 裡的 Trace。

---

# ⑪ Evidence：打開 LangSmith

進入 LangSmith：

```text
learning-sre-ai-era-day01
```

找到剛剛產生的 Trace。

理想上會看到：

```text
ask_workflow
│
├── build_prompt
│
└── Gemini
```

今天只觀察幾個欄位：

| Trace 資訊       | 今天觀察什麼？     | 未來 SRE 意義          |
| ---------------- | ------------------ | ---------------------- |
| Trace / Run ID   | 是否能識別單次執行 | Incident correlation   |
| Workflow Latency | 整條 Request 多久  | End-to-end latency     |
| Model Latency    | Gemini 花多久      | Dependency latency     |
| Prompt           | Model 實際看到什麼 | Prompt debugging       |
| Model            | 實際使用哪個模型   | Change management      |
| Input Tokens     | Context 大小       | Capacity / Cost        |
| Output Tokens    | 生成量             | Cost / Throughput      |
| Error            | 哪一步失敗         | Failure localization   |
| Output           | 最後產生什麼       | Semantic investigation |

原本我們只有：

```text
POST /ask
HTTP 200
```

現在變成：

```text
ask_workflow                  1.82s
│
├── build_prompt               1ms
│
└── Gemini                    1.79s
    ├── Model
    ├── Prompt
    ├── Input Tokens
    ├── Output Tokens
    └── Response
```

原本的 AI 黑盒子開始有輪廓了。

---

# ⑫ 第一個故障實驗：故意把 Model 搞壞

這次先主動製造一次故障：

> **不要等 Production 壞給你看。**

自己先把它弄壞。

把：

```env
MODEL_NAME=gemini-2.5-flash
```

改成：

```env
MODEL_NAME=definitely-not-a-real-model
```

重新啟動 Application。

再呼叫：

```bash
curl \
  -X POST \
  http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is an SLO?"
  }'
```

FastAPI 應該會回：

```text
502 Bad Gateway
```

只有 HTTP 時：

```text
POST /ask → 502
```

我們得到的資訊是：

> 壞了。

謝謝。

非常有幫助。
![呵呵](https://memeprod.sgp1.digitaloceanspaces.com/user-wtf/1654398658424.jpg)

但 Trace 可能看到：

```text
ask_workflow
│
├── build_prompt       SUCCESS
│
└── Gemini             ERROR
```

Failure Domain 馬上縮小：

```text
FastAPI Endpoint？
至少有收到 Request。

Prompt Construction？
成功。

Gemini Call？
失敗。
```

這次故障顯示，Observability 能縮小 Failure Domain：

> **收集資料的目的，是降低未知數。**

---

# ⑬ 如果 P95 Latency 突然變成 15 秒呢？

再來一個更接近 Production 的情境。

假設 Dashboard 告訴你：

```text
P95 Latency = 15 seconds
```

問題可能出現在：

- FastAPI
- PostgreSQL
- Prompt Length
- Gemini
- Input Tokens
- Output Tokens
- Retry
- Network
- Tool Call
- Queue

沒有 Trace：

```text
¯\_(ツ)_/¯
```

![窩不知道](https://megapx-assets.dcard.tw/images/cd3a3ca1-b13b-4db1-9895-d748f2bab036/640.jpeg)

大家輪流猜。

有 Trace：

```text
Request                         15.2s
├── build_prompt                  2ms
└── Gemini                      15.1s
```

至少知道：

> Application Logic 大概不是主要瓶頸。

未來加入 RAG 後可能變成：

```text
Request                         15.2s
├── build_prompt                  2ms
├── retrieval                   11.8s
└── Gemini                       3.1s
```

答案馬上變了。

Trace 不會讓 Failure 消失。

它做的是讓你從：

```text
我覺得問題在這裡。
```

變成：

```text
Evidence 顯示問題在這裡。
```

---

# ⑭ AI Observability 到底多觀察了什麼？

傳統 Service 通常會關心：

```text
Availability
Latency
Errors
Traffic
CPU
Memory
Database
Network
```

AI Application 除了這些之外，又開始增加：

```text
Prompt
Model
Tokens
Retrieval
Tools
Retries
Cost
Evaluation
```

未來完整 Workflow 可能長成：

```text
Client
  ↓
API
  ↓
Prompt / Policy
  ↓
Retriever
  ├── Query
  ├── Vector DB
  └── Document IDs
  ↓
Model Router
  ↓
Gemini / Other Provider
  ├── Model
  ├── Tokens
  ├── Latency
  └── Cost
  ↓
Tool Executor
  ├── Tool
  ├── Input
  ├── Output
  └── Latency
  ↓
Validator
  ↓
Response
```

Trace 裡也可能慢慢出現：

```text
prompt_version
retrieval_query
document_ids
embedding_model
provider
model_version
tool_name
tool_latency
agent_step_count
retry_count
input_tokens
output_tokens
cost
evaluation_label
safety_decision
```

所以：

> **AI Observability 不是在 Prometheus 多加幾個 Gemini Metrics。**

而是：

> **Reliability 的觀測邊界開始深入 AI Workflow。**

---

# ⑮ Trace 可以告訴我們答案是對的嗎？

現在回到文章最一開始。

假設 Trace 顯示：

```text
API             SUCCESS
Prompt          SUCCESS
Gemini          SUCCESS
Parser          SUCCESS
```

LLM 最後回答：

```text
員工一年有 30 天特休。
```

結果：

**還是錯的。**

Trace 能夠告訴我們：

> 系統怎麼產生這個答案。

但它不一定能告訴我們：

> 這個答案是否正確。

所以 AI Application 會出現三個不同層級：

```text
Technical Success
        ≠
Workflow Success
        ≠
Task Success
```

也就是：

```text
HTTP 200
        ≠
Workflow 正常
        ≠
使用者得到正確答案
```

這也是後續會正式討論：

- Groundedness
- Relevance
- Golden Dataset
- LLM Evaluation
- Task Success Rate
- Safety Evaluation

的原因。

> **Observability ≠ Evaluation。**

Observability 回答：

> 發生了什麼？

Evaluation 才開始回答：

> 結果夠不夠好？

---

# ⑯ 那傳統 Metrics 還重要嗎？

重要，因為 Metrics 適合觀察整體趨勢。

用了 LangSmith，不代表：

```text
Prometheus
Logs
OpenTelemetry
```

突然全部可以丟掉。

假設 Production 一小時有：

```text
100,000 Requests
```

你不會打開 100,000 條 Trace 開始手算：

```text
Error Rate 是多少？
```

Metrics 更擅長回答：

```text
整體趨勢
Error Rate
P95
P99
Traffic
Saturation
```

Trace 更擅長：

```text
單一 Request
到底去哪裡慢
到底在哪裡失敗
```

Logs 則幫助我們理解：

```text
具體發生什麼事件
Exception 是什麼
Application 寫了哪些狀態
```

未來整體關係會變成：

```text
Prometheus
    ↓
發現 P95 Latency 異常
    ↓
Trace
    ↓
找到 Gemini Dependency 變慢
    ↓
Logs
    ↓
查看實際 Error / Retry 資訊
```

所以不是：

```text
Metrics vs Logs vs Traces
```

而是：

```text
Metrics + Logs + Traces
```

Day 21 我們會正式回來把三者串起來。

---

# ⑰ 為什麼今天直接用 Google Gen AI SDK？

Gemini 本身也提供 OpenAI-compatible API。

但 Day 1 我們刻意使用：

```text
google-genai
```

而不是：

```text
OpenAI SDK
 ↓
Gemini OpenAI-compatible Endpoint
```

原因很簡單：

今天要回答的是：

> **一條 AI Workflow 到底怎麼執行？**

而不是：

> 怎麼設計 Multi-provider Abstraction？

這兩件事情不要第一天混在一起。

未來進入：

- Provider Failure
- Failover
- Retry
- Circuit Breaker
- Model Routing
- Multi-provider

時，我們會再把架構演進成：

```text
Application
     ↓
Provider Abstraction
     ↓
┌───────────┬───────────┐
│  Gemini   │ Provider B│
└───────────┴───────────┘
```

Day 1 保持簡單：

```text
Application
 ↓
Gemini
```

**不要太早抽象。**

尤其當你現在只有一個 Provider。

---

# ⑱ Production Takeaway

今天沒有建立什麼巨大平台。

只有：

```text
FastAPI
  ↓
Prompt
  ↓
Gemini
  ↓
Response
```

再加上一件事：

```text
Trace
```

但就是這一條 Trace，把原本只有：

```text
HTTP 200
```

的世界，擴展成：

```text
Request
├── Prompt
├── Model
├── Latency
├── Tokens
├── Error
└── Output
```

傳統 Service Reliability 會問：

> Request 有沒有成功完成？

AI Reliability 還必須繼續問：

> 它怎麼完成？

> 經過哪些步驟？

> 依賴哪些 External Dependencies？

> 哪一段最慢？

> 使用哪個 Model？

> 花了多少 Tokens？

> 發生 Retry 了嗎？

> 最後產生什麼結果？

甚至：

> 這個結果值得使用者相信嗎？

---

# Day 1 的重點不在 LangSmith

如果今天只能記住一件事。

不要記：

```python
wrap_gemini()
```

也不要記：

```env
LANGSMITH_TRACING=true
```

> **當 Application 從 deterministic request 變成 AI workflow，我們需要觀測的邊界，也必須跟著深入 Workflow。**

LangSmith 今天只是讓我們快速看見這條 Workflow 的工具。

工具之後可以換。

未來即使變成：

```text
OpenTelemetry
 ↓
OTLP
 ↓
Tempo / Jaeger
```

我們仍然要回答：

```text
Instrument
 ↓
Propagate Context
 ↓
Record Execution
 ↓
Export Telemetry
```

Tracing 的概念不會因為工具改變。

---

# 下一篇：Day 02｜建立自己的 SRE Lab

Day 1 才剛把 Gemini 接起來。

Day 2 我們反而要先把 AI 放旁邊。

因為：

> 再漂亮的 LLM Trace，也不能取代 Reliability Engineering 的基本功。

下一篇我們會建立整個系列共用的 SRE Lab：

```text
Client
  ↓
FastAPI
  ├── PostgreSQL
  ├── Redis
  ├── Prometheus
  ├── Loki
  ├── OpenTelemetry
  └── Grafana
```

全部透過 Docker Compose 啟動。

然後正式開始：

```text
Build
  ↓
Break
  ↓
Observe
  ↓
Explain
```

最後再一路把它演化回 AI Workflow：

```text
Build
  ↓
Trace
  ↓
Break
  ↓
Measure
  ↓
Evaluate
  ↓
Recover
  ↓
Improve
```

---

> 這篇是 **Learning SRE for the AI Era** 系列的一部分。
>
> 我會從 SRE 的服務可靠性基礎開始，逐步探索當系統加入 LLM、RAG、Agent 與 GPU Infrastructure 後，如何讓 AI 系統不只可用，也能被觀測、評估、控制成本並安全演進。
>
> **Build → Trace → Break → Measure → Evaluate → Recover → Improve.**
