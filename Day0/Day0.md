# Day 00｜從零建立開發環境：Python、uv、Gemini API Key 與 LangSmith

**Setting Up the Lab Before We Break Things**

在 Day 1，我們會建立第一條 AI Workflow Trace：

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

然後用 LangSmith 把這條 request 打開來看。

技術教學常把這一步寫成：

> 「請先自行準備開發環境與 API Key。」

**恭喜，你的第一個 Bug 已經開始了。**

所以 Day 0 不談 Reliability、不談 SLO，也不談 Observability。

Day 0 的目標很簡單：準備好後續 30 天需要的開發環境，並確認它能呼叫 Gemini。

完成後，環境裡會有：

- Python 開發環境
- `uv` 套件管理工具
- 一個 Python 專案
- Google AI Studio Gemini API Key
- LangSmith API Key
- `.env` Secret Management
- Google Gen AI SDK
- 第一個 Gemini API Smoke Test

Day 1 就能開始 tracing。

---

# ① 今天要準備什麼？

先把環境縮到能完成 Day 0 與 Day 1 的範圍：

```text
Local Machine
│
├── Python
├── uv
│
└── Python Project
    │
    ├── FastAPI
    ├── google-genai
    ├── LangSmith
    └── .env
```

我們需要兩個外部服務：

```text
Google AI Studio
      ↓
GEMINI_API_KEY
      ↓
Gemini API
```

以及：

```text
LangSmith
    ↓
LANGSMITH_API_KEY
    ↓
Trace Storage / Visualization
```

最終 `.env` 大概會是：

```env
GEMINI_API_KEY=your_gemini_api_key

LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=learning-sre-ai-era-day01

MODEL_NAME=gemini-3.7-flash
```

先不要把 Key 貼進任何 Python 程式碼。

---

## 為什麼這個系列先選 Gemini？

這個系列第一階段先使用 **Google Gemini API**，目的是降低學習門檻，不比較哪一家 LLM 最強。

我們真正想學的是：

```text
SRE
Observability
Tracing
SLI / SLO
Failure Handling
AI Reliability
```

而不是第一天就先處理一筆 LLM API 帳單。

```text
Google AI Studio
      ↓
Gemini API Key
      ↓
Google Gen AI SDK
```

### 1. AI Studio 有免費使用額度

對教學與個人 Lab 來說，低成本足以支撐早期實驗。

Day 1 的 Request 數量很少，我們只會：

```text
Send Request
    ↓
Observe Trace
    ↓
Break Something
    ↓
Send Again
```

不需要為了學一條 Trace，先處理付費設定。

不過要注意：

> **免費額度不是「無限免費」。**

實際 Rate Limit、可用 Model 與 Quota 仍會依 Google 當下政策與帳戶設定而異。

所以未來進入 Load Testing、大量 Evaluation 或 Production Experiment 時，成本仍然會是我們需要觀察的一項 Reliability 指標。

---

### 2. 官方 Python SDK 的最小呼叫

Google 提供：

```text
google-genai
```

最小的 LLM Call 只需要以下幾行：

```python
from google import genai

client = genai.Client()

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="What is an SLO?",
)
```

Day 0 與 Day 1 先聚焦 Request、Workflow 與 Trace，不展開 SDK abstraction。

---

### 3. 這個系列不比較 Provider

> **我們選 Gemini，不代表後面的 Reliability 架構會綁死 Gemini。**

今天可能是：

```text
FastAPI
  ↓
Gemini
```

未來可能變成：

```text
Application
     ↓
Model Router
     ↓
├── Gemini
├── OpenAI
├── Anthropic
└── Local Model
```

到了後面的：

- Dependency Reliability
- Provider Failover
- Retry
- Circuit Breaker
- Model Routing
- Cost Control

我們反而會刻意把 LLM Provider 當成：

```text
External Dependency
```

來處理。

Day 0 選 Gemini，是因為成本低、容易開始，足以讓我們先練習 Reliability。

工具之後可以換。

但：

```text
Build
 ↓
Trace
 ↓
Break
 ↓
Measure
 ↓
Recover
```

這套思考方式不會因為 Model Provider 改變。

---

# ② 安裝 uv

這個系列的 Python 環境統一使用：

```text
pyproject.toml
+
uv
```

不使用傳統的：

```text
requirements.txt
pip install
python -m venv
```

不是因為 `pip` 不能用。

我希望整個 Lab 的環境能做到：

- 重現
- Lock dependency
- 管理 Python version
- 建立 virtual environment
- 統一開發指令

`uv` 剛好可以把這些事情整合在一起。

官方支援 macOS、Linux 與 Windows。

---

## macOS

如果你有 Homebrew：

```bash
brew install uv
```

或者直接使用官方 installer：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安裝後確認：

```bash
uv --version
```

只要看到類似：

```text
uv 0.x.x
```

就代表成功。

---

## Linux

使用官方 installer：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

如果沒有 `curl`：

```bash
wget -qO- https://astral.sh/uv/install.sh | sh
```

重新開啟 Terminal 後：

```bash
uv --version
```

Astral 官方目前就是建議透過 standalone installer 安裝。

---

## Windows

PowerShell：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

或者使用：

```powershell
winget install --id=astral-sh.uv -e
```

然後：

```powershell
uv --version
```

能看到版本就完成。

---

# ③ Python 也交給 uv 管

你可以先確認目前 Python：

```bash
python --version
```

但如果沒有安裝 Python，也不用急著去 Python 官網找 installer。

`uv` 本身可以管理 Python。

我們這個系列先使用：

```text
Python 3.14
```

安裝：

```bash
uv python install 3.14
```

確認：

```bash
uv python list
```

這也是我偏好 `uv` 的原因之一。

之後進到 CI、Docker 或不同電腦時：

```text
Python Environment
```

會少很多：

> 「可是我這台可以跑啊。」

這種經典 Production 前傳。

---

# ④ 建立第一個專案

建立：

```bash
mkdir sre-for-ai-era
cd sre-for-ai-era
```

初始化：

```bash
uv init --python 3.14
```

這時會得到類似：

```text
sre-for-ai-era/
├── .python-version
├── README.md
├── main.py
└── pyproject.toml
```

打開：

```text
pyproject.toml
```

大概會看到：

```toml
[project]
name = "sre-for-ai-era"
version = "0.1.0"
description = "Learning SRE for the AI Era"
requires-python = ">=3.14"
dependencies = []
```

之後 Python 專案的 dependency 都由這個檔案管理。

---

# ⑤ 安裝 Day 0 / Day 1 需要的套件

執行：

```bash
uv add \
  fastapi \
  "uvicorn[standard]" \
  google-genai \
  langsmith \
  pydantic-settings
```

完成後：

```text
pyproject.toml
```

會自動出現 dependencies。

同時通常還會產生：

```text
uv.lock
```

完成這一步後，Repository 會包含：

```text
sre-for-ai-era/
├── .python-version
├── pyproject.toml
├── uv.lock
├── README.md
└── main.py
```

`uv.lock` 建議 Commit。

因為：

> `pyproject.toml` 說我們需要什麼。

而：

> `uv.lock` 更接近告訴我們實際解析出了什麼版本。

這對後續建立可重現環境很重要。

---

# ⑥ 取得 Gemini API Key

接著來處理第一把 Key。

我們要使用：

# Google AI Studio

Google AI Studio 是 Google 提供的 Gemini 開發入口，可以：

- 測試 Prompt
- 試不同 Gemini Model
- 查看 API Usage
- 管理 Projects
- 建立 Gemini API Key

Google 官方目前的新專案可以直接從 AI Studio 建立 Gemini API Key。

---

## Step 1：進入 Google AI Studio

前往 Google AI Studio。

[Google AI Studio](https://aistudio.google.com)

登入 Google Account。

---

## Step 2：進入 API Keys

進入 Dashboard 後找到：

```text
API Keys
```

如果是第一次使用，Google 可能會要求你：

- 接受 Terms of Service
- 建立預設 Google Cloud Project

新使用者在接受條款後，AI Studio 可以自動建立預設 Project；如果你本身已有 Google Cloud 帳戶，也可以 Import 已存在的 Project。

---

## Step 3：Create API Key

點：

```text
Create API key
```

選擇要使用的 Project。

建立後會拿到一串 Key。

例如：

```text
xxxxxxxxxxxxxxxxxxxxxxxx
```

**不要把可用的 API Key 截圖貼在文章、Discord、Slack、GitHub Issue 或 README。**

這不是：

```text
Project ID
```

這組 Credential 可以直接呼叫 API。

---

## 2026 年需要注意：Gemini API Key 正在改版

如果你以前建立過 Gemini Key，請先確認它的類型。

Google 正在把 Gemini API 從舊的 **Standard API Key** 遷移至新的 **Authorization Key**。

> 在 Google AI Studio 新建立的 API Key，預設已經是新的 Auth Key。

Google 官方也表示，**2026 年 9 月開始 Gemini API 將拒絕 Standard Key**。

重新建立環境時，請直接：

> **直接建立新的 AI Studio Key，不要拿幾年前的舊 Key 硬撐。**

---

# ⑦ API Key 不要寫進 Python

不要把 API Key 寫進 Python：

```python
from google import genai

client = genai.Client(
    api_key="YOUR_REAL_KEY"
)
```

Technically：

```text
可以跑。
```

Engineering：

```text
不要。
```

因為你的下一個動作很可能是：

```bash
git add .
git commit -m "day 0 done"
git push
```

然後：

**Day 0 就順便學 Credential Incident Response。**

---

## 使用 Environment Variable

Google 官方建議設定：

```text
GEMINI_API_KEY
```

Google Gen AI SDK 會自動讀取它。

但我們不把 Secret 永久寫進 shell profile。

對這個 Lab，我比較推薦：

```text
.env
```

---

# ⑧ 建立 `.env`

Project Root 建立：

```text
.env
```

加入：

```env
GEMINI_API_KEY=你的_Gemini_API_Key
```

例如：

```env
GEMINI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
```

接著建立：

```text
.env.example
```

內容只放 Placeholder：

```env
GEMINI_API_KEY=your_gemini_api_key
```

差別：

```text
.env
```

是：

> 你自己的 Secret。

而：

```text
.env.example
```

是：

> 告訴其他 Developer 這個 Application 需要哪些環境變數。

---

# ⑨ 第一件事：建立 `.gitignore`

如果這一步忘記，前面講的 Security 全部當作沒講。

建立：

```text
.gitignore
```

內容至少：

```gitignore
.env
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

確認：

```bash
git status
```

你應該：

**看不到 `.env`。**

如果看到 `.env`，先不要 Commit。

---

## `.env.example` 要 Commit

正確情況是：

```text
.env              ❌ Git ignored
.env.example      ✅ Git tracked
```

例如：

```env
# .env.example

GEMINI_API_KEY=your_gemini_api_key
```

這樣可以讓其他人取得設定範本，又不會拿到你的 Credential。

---

# ⑩ 測試 Gemini API Key

在正式碰 FastAPI 之前，我們先做：

## Smoke Test

先確認：

```text
Local Python
  ↓
Google SDK
  ↓
Authentication
  ↓
Gemini API
```

先確認這條路徑能完成一次 Gemini API 呼叫。

建立：

```text
scripts/test_gemini.py
```

---

## 新專案改用 Interactions API

截至 2026 年，Google 已經將：

### Interactions API

新專案預設使用 Gemini Interface。

Google 官方說明，從 **2026 年 6 月開始**，Interactions API 已經成為推薦的新介面，而早期常見的：

```text
generateContent
```

仍然支援，但已被視為 legacy。

Day 0 的 Gemini Smoke Test 直接使用新的 Interactions API。

---

## 建立 Smoke Test

```python
from google import genai


client = genai.Client()

interaction = client.interactions.create(
    model="gemini-3.7-flash",
    input="Reply with exactly: Gemini connection OK",
)

print(interaction.outputs[-1].text)
```

```python
genai.Client()
```

沒有傳：

```python
api_key=
```

因為 SDK 可以直接讀：

```text
GEMINI_API_KEY
```

Google 官方 Quickstart 現在也是以 `client.interactions.create()` 示範新的 Interactions API。

---

## 但是 `.env` 怎麼載入？

剛剛的 SDK 會讀 OS Environment Variable。

但我們目前把 Key 放在：

```text
.env
```

Day 0 先用 `pydantic-settings` 載入設定。

建立：

```text
app/config.py
```

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Smoke Test 改成：

```python
from google import genai

from app.config import get_settings


settings = get_settings()

client = genai.Client(
    api_key=settings.gemini_api_key,
)

interaction = client.interactions.create(
    model="gemini-3.7-flash",
    input="Reply with exactly: Gemini connection OK",
)

print(interaction.outputs[-1].text)
```

執行：

```bash
uv run python scripts/test_gemini.py
```

如果看到：

```text
Gemini connection OK
```

代表這整條：

```text
Python
 ↓
.env
 ↓
Google Gen AI SDK
 ↓
Authentication
 ↓
Gemini
```

已經成功。

---

## 如果出現 Authentication Error 呢？

先不要開始：

```text
重裝 Python
重裝 VS Code
重開電腦
懷疑人生
```

先縮小問題。

檢查：

```text
.env
```

是否真的存在：

```bash
ls -la
```

確認：

```env
GEMINI_API_KEY=...
```

變數名稱有沒有拼錯。

最常見的是：

```env
GEMINI_KEY=
```

但程式找的是：

```text
GEMINI_API_KEY
```

這兩個不是同一個東西。

---

## 測試 Config 有沒有讀到 Key

可以暫時：

```python
print(bool(settings.gemini_api_key))
```

期待：

```text
True
```

**不要：**

```python
print(settings.gemini_api_key)
```

Debug Secret 時，不要把 Secret 印到 Log。

---

# ⑪ 取得 LangSmith API Key

Gemini 已經能跑。

接下來準備 Day 1 的第二把 Key：

## LangSmith API Key

Day 1 我們會使用 LangSmith 儲存與視覺化：

```text
ask_workflow
├── build_prompt
└── Gemini
```

因此 Application 需要權限，才能把 Trace 傳給 LangSmith。

---

## Step 1：建立 LangSmith Account

進入 LangSmith：

[LangSmith](https://smith.langchain.com)

官方目前支援：

- Google
- GitHub
- Email
- Discord

登入。

---

## Step 2：進入 Settings

進入：

```text
Settings
  ↓
API Keys
```

選：

```text
Create API Key
```

LangSmith 目前主要有兩種：

### Personal Access Token

適合：

```text
Developer
Local development
Personal scripts
```

### Service Key

適合：

```text
Application
Production service
Automation
```

這裡把 Personal Access Token 用於本機開發，把 Service Key 留給 Application、Production 與 Automation。

---

## Day 0 用哪個？

我們現在只是：

```text
Local Lab
```

所以建立：

```text
Personal Access Token
```

就足夠。

Production 之後再用：

```text
Service Key
```

不要第一天就把：

```text
Local Developer Credential
```

和：

```text
Production Workload Identity
```

搞成同一件事。

---

## Step 3：建立 Key

給它一個名稱，例如：

```text
sre-for-ai-era-local
```

建立後，LangSmith 只會完整顯示 API Key 一次。請當場安全保存。

你會得到類似：

```text
lsv2_...
```

---

# ⑫ 把 LangSmith Key 加進 `.env`

現在：

```env
GEMINI_API_KEY=your_gemini_api_key

LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=learning-sre-ai-era-day01
```

LangSmith 官方 tracing 需要至少：

```env
LANGSMITH_API_KEY=...
LANGSMITH_TRACING=true
```

設定 `LANGSMITH_PROJECT` 後，Trace 會進入指定 Project。

否則最後可能只剩一個 default Project，裡面堆著 8,000 條不知道屬於誰的 Trace。

---

# ⑬ 完成 `.env.example`

提交到 Repository 的 `.env.example`：

```env
GEMINI_API_KEY=your_gemini_api_key

LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=learning-sre-ai-era-day01

MODEL_NAME=gemini-3.7-flash
```

實際使用的 `.env`：

```env
GEMINI_API_KEY=你的真正_Key

LANGSMITH_API_KEY=你的真正_Key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=learning-sre-ai-era-day01

MODEL_NAME=gemini-3.7-flash
```

兩者的差異在於：

```text
.env.example
```

`.env.example` 不應包含實際 Credential。

---

# ⑭ 最終 Project Structure

Day 0 完成後，大概會是：

```text
sre-for-ai-era/
├── app/
│   ├── __init__.py
│   └── config.py
├── scripts/
│   └── test_gemini.py
├── .env
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
└── README.md
```

目前還沒有這些元件，這是正常的。

```text
FastAPI Endpoint
LangSmith Trace
Prometheus
Grafana
PostgreSQL
Redis
OpenTelemetry
```

今天是：

# Day 0

不是：

# Day 0：順便重建 Google Cloud。

---

# ⑮ 最後做一次 Environment Check

依序執行：

```bash
uv --version
```

再來：

```bash
uv run python --version
```

應該是：

```text
Python 3.14.x
```

確認 dependency：

```bash
uv sync
```

最後：

```bash
uv run python scripts/test_gemini.py
```

如果輸出：

```text
Gemini connection OK
```

今天就完成了。

---

# Day 0 Checklist

- [ ] 安裝 `uv`
- [ ] 安裝 / 管理 Python 3.14
- [ ] 建立 `sre-for-ai-era`
- [ ] 建立 `pyproject.toml`
- [ ] 安裝 `google-genai`
- [ ] 安裝 FastAPI
- [ ] 安裝 LangSmith
- [ ] 建立 Google AI Studio Project
- [ ] 建立新的 Gemini API Key
- [ ] 建立 LangSmith API Key
- [ ] 建立 `.env`
- [ ] 建立 `.env.example`
- [ ] `.gitignore` 排除 `.env`
- [ ] Gemini Smoke Test 成功

只要全部打勾：

**Day 1 可以開工。**

---

# ⑯ Security Lesson：先保護 API Key

今天還沒正式講 SRE。

不過，我們已經碰到第一個 Production Reliability 問題：

# Secret Management

一個被 GitHub 公開的 API Key 可能造成：

- Unauthorized Requests
- Quota Exhaustion
- Unexpected Billing
- Service Disruption
- Credential Rotation
- Incident Investigation

所以：

```text
API Key management
```

不是單純：

> 「不要把密碼貼出去。」

它本身就是 Reliability 與 Security 的一部分。

如果 Key 不小心 Commit：

不要只有：

```bash
git rm .env
```

因為 Credential 很可能已經進入 Git History。

第一步是 **Rotate / Revoke Credential。**

Google 官方對洩漏 Key 的處理也是先建立 replacement、更新 Application，再停用或刪除 compromised key，並檢查 usage。

不要賭：

> 「應該沒人看到吧。」

Internet 在這方面通常比你想像中勤勞。

---

# ⑰ Day 0 學到了什麼？

表面上今天只做了：

```text
Install uv
Get API Keys
Run Gemini
```

同時也建立了幾個後面會反覆用到的工程習慣：

```text
Reproducible Environment
Secret Separation
Dependency Management
Configuration Management
Smoke Testing
```

這些看起來沒有 LLM Agent 那麼酷。

但 Production 系統真正容易把人叫起床的，通常也不是：

```text
Transformer Architecture
```

而是：

```text
Environment 不一致
Credential 過期
Configuration 寫錯
Dependency 壞掉
Service 根本連不到 Provider
```

所以在開始研究：

> 「AI 時代的 SRE 有什麼不同？」

之前，我們先確保最基本的軟體工程沒有消失。

---

# 下一篇：Day 01｜用 LLM Trace 看見一次 AI Workflow

環境準備好了。

下一篇會建立：

```text
Client
  ↓
FastAPI
  ↓
Prompt Construction
  ↓
Gemini
  ↓
Response
```

然後加上 LangSmith。

讓原本只能看到：

```text
HTTP 200
```

的 Request，第一次變成：

```text
ask_workflow
│
├── build_prompt
│
└── Gemini
    ├── Model
    ├── Prompt
    ├── Latency
    ├── Tokens
    └── Output
```

> **當 API 成功，但 AI 回答錯了，我們到底應該觀察什麼？**

---

> 這篇是 **Learning SRE for the AI Era** 系列的環境準備篇。
>
> 從 Day 1 開始，我們會從一條最小 LLM Trace 出發，逐步建立 SRE Lab、SLI/SLO、Observability、Incident Response 與 Resilience，再延伸到 LLM、RAG、Agent 和 GPU Infrastructure。
