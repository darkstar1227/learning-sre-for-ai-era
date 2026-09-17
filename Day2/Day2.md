> GitHub：[darkstar1227/learning-sre-for-ai-era](https://github.com/darkstar1227/learning-sre-for-ai-era)

**Building an SRE Lab with FastAPI, Docker, Prometheus, Grafana, Loki, Tempo, and OpenTelemetry**

昨天，我們做了一件有點超前進度的事情。

我們直接把一條 AI Request 打開：

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

接著用 LangSmith 看見：

```text
ask_workflow
├── build_prompt
└── Gemini
```

第一次知道：

> HTTP 200 背後，還藏著一整條 AI Workflow。

但今天，我們反而先把 Gemini 放旁邊。

因為在開始討論：

```text
LLM
RAG
Agent
GPU
Evaluation
```

以前，得先把一件事做好。

## **我們需要一個可以被弄壞的系統。**

---

# ① 為什麼我們需要自己的 SRE Lab？

學 Prometheus 很簡單。

搜尋：

```text
Prometheus Tutorial
```

學 Grafana 也不難。

搜尋：

```text
Best Grafana Dashboard
```

Incident Response？

可以閱讀 Google、Cloudflare、GitHub 的 Postmortem。

問題是：

> **如果你永遠只看別人的事故，你很難真正建立 Reliability 的直覺。**

例如有人告訴你：

```text
P99 latency 很重要。
```

你可能知道。

但如果自己沒有看過：

```text
P50 = 120 ms
P95 = 180 ms
P99 = 8.7 s
```

你很難真正感受到：

> 平均值到底可以騙人到什麼程度。

Google 的 Jeffrey Dean 與 Luiz André Barroso 在 [The Tail at Scale](https://www.barroso.org/publications/TheTailAtScale.pdf) 講得更直白：系統一大，平均延遲幾乎沒有意義，因為使用者實際感受到的是那條長尾——P99、甚至 P99.9。一個服務有上百個依賴同時處理一個 Request 時，只要有一小部分機率變慢，整體被慢請求拖累的比例會遠高於你以為的「一小部分」。

又例如：

```text
Retry 要搭配 backoff。
```

聽起來合理。

直到有一天你自己做出：

```text
Dependency slowdown
        ↓
Client retry
        ↓
More traffic
        ↓
Dependency slower
        ↓
More retries
        ↓
Congratulations
```

你才會知道：

> Retry 有時候不是救火，是在旁邊倒汽油。

USENIX 那篇 [Metastable Failures in the Wild](https://www.usenix.org/publications/loginonline/metastable-failures-wild) 分析的正是這種現象：系統本來只是暫時變慢，卻因為 retry 沒有 backoff，讓額外流量把負載愈墊愈高，最後系統卡在一個「移除誘因後也回不去正常狀態」的 metastable 狀態。小故障被自己的重試機制放大成大故障。

![提油救火](https://memeprod.sgp1.digitaloceanspaces.com/user-wtf/1613913002223.jpg)

所以整個系列會建立自己的：

## SRE Lab

它不模擬 Fortune 500 公司的 Production Infrastructure，只建立一個：

> **最小、可重現、可觀測、可擴充，而且可以放心故意弄壞的系統。**

---

# ② 這個 Lab 要能做什麼？

接下來 30 天，我希望可以對同一套環境反覆做：

```text
Build
  ↓
Observe
  ↓
Break
  ↓
Measure
  ↓
Explain
  ↓
Recover
```

例如：

```text
HTTP 500
Timeout
Database unavailable
Redis unavailable
Container crash
Memory pressure
Dependency slowdown
Retry storm
Queue backlog
```

然後問：

- Metrics 看到了什麼？
- Logs 看到了什麼？
- Trace 看到了什麼？
- Alert 有沒有響？
- 服務有沒有恢復？

未來再慢慢加入：

```text
LLM
RAG
Vector DB
Tool Calling
Agent
Evaluation
GPU inference
Provider fallback
```

今天要建立後續 Reliability Experiment 共用的實驗平台。工具不少，但工具本身不是主角。

---

# ③ 今天要建立的架構

最終架構會長這樣：

```text
                         ┌──────────────┐
                         │    Client    │
                         │ curl / k6    │
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │   FastAPI    │
                         └──────┬───────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
              ┌──────────┐             ┌──────────┐
              │PostgreSQL│             │  Redis   │
              └──────────┘             └──────────┘


                         Observability
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
       Metrics               Logs                Traces
          │                    │                    │
          ▼                    ▼                    ▼
     Prometheus              Alloy         OpenTelemetry
                               │             Collector
                               ▼                    │
                              Loki                  ▼
                                                  Tempo
          │                    │                    │
          └────────────────────┼────────────────────┘
                               ▼
                            Grafana
```

今天 FastAPI 實際要做到的只有：

```text
Client
  ↓
FastAPI
  ├── /metrics → Prometheus
  ├── JSON logs → Docker → Alloy → Loki
  └── traces → OTel Collector → Tempo
```

PostgreSQL 和 Redis 先跑起來。

但今天：

**不要寫 CRUD。**

不要：

```text
User Table
Migration
Repository Pattern
Authentication
JWT
RBAC
```

否則 Day 2 最後會變成：

# 「歡迎來到 SQLAlchemy migration debugging。」

這不是我們今天的主題。

---

# ④ 先修正一個 2026 年的 Observability Stack

如果你幾年前看過 Grafana 教學，很可能看過：

```text
Promtail
 ↓
Loki
```

因此，本系列的新專案不再從 Promtail 開始。

Promtail 已經在 **2026 年 3 月 2 日正式 EOL**，Grafana 現在建議改用：

```text
Grafana Alloy
```

Alloy 可以直接發現 Docker containers、讀取 container logs，再送進 Loki。

這個系列改用：

```text
Docker Logs
    ↓
Grafana Alloy
    ↓
Loki
```

而不是：

```text
Docker Logs
    ↓
Promtail
    ↓
Loki
```

這也帶出 Reliability Engineering 很重要的一個觀念：

> **可重現，不代表永遠凍結在舊技術。**

好的 Lab 應該穩定。

但不能穩定到變化石。
![化石](https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSElkVUNN8WaA6sxrY0yczheXiZVoHNvf_LyPoYjZe9b9yXSY0-H-YANejJ&s=10)

---

# ⑤ OpenTelemetry Collector 不是 Trace Backend

另一個常見誤解是：

```text
FastAPI
 ↓
OpenTelemetry Collector
```

OpenTelemetry Collector 收到 Trace，不代表 Trace 已經有地方長期儲存與查詢。

OpenTelemetry Collector 比較像：

```text
Telemetry Pipeline
```

負責：

```text
Receive
Process
Export
```

它本身不是你用來長期儲存和查詢 traces 的地方。

所以今天我們另外加入：

```text
Grafana Tempo
```

整條路徑變成：

```text
FastAPI
 ↓
OTLP
 ↓
OpenTelemetry Collector
 ↓
OTLP
 ↓
Tempo
 ↓
Grafana
```

OpenTelemetry 官方也建議讓 Application 透過 OTLP exporter 將 telemetry 送到 Collector，再由 Collector 送到真正的 backend。

這一層非常重要。

因為它讓 Application 不必知道：

```text
Tempo
Jaeger
Grafana Cloud
Datadog
Honeycomb
Vendor X
```

Application 只知道：

```text
OTLP
```

這就是：

# Vendor-neutral instrumentation

未來換 backend，不一定要把 Application 全部重寫。

---

# ⑥ 今天完成後的專案結構

延續 Day 0 的 `uv + pyproject.toml`，今天我們把 Repository 長成：

```text
sre-for-ai-era/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── logging.py
│   ├── main.py
│   ├── metrics.py
│   └── telemetry.py
│
├── observability/
│   ├── prometheus/
│   │   └── prometheus.yml
│   │
│   ├── grafana/
│   │   └── provisioning/
│   │       └── datasources/
│   │           └── datasources.yml
│   │
│   ├── loki/
│   │   └── loki-config.yml
│   │
│   ├── alloy/
│   │   └── config.alloy
│   │
│   ├── tempo/
│   │   └── tempo.yml
│   │
│   └── otel/
│       └── collector-config.yml
│
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
└── uv.lock
```

每個檔案只負責一件事情。

| 檔案                   | 責任                                    |
| ---------------------- | --------------------------------------- |
| `app/main.py`          | FastAPI endpoints 與 middleware         |
| `app/metrics.py`       | Prometheus application metrics          |
| `app/logging.py`       | JSON structured logging                 |
| `app/telemetry.py`     | OpenTelemetry trace 初始化              |
| `prometheus.yml`       | Prometheus scrape targets               |
| `config.alloy`         | Docker log discovery 與 Loki forwarding |
| `loki-config.yml`      | Log backend                             |
| `collector-config.yml` | OTLP telemetry pipeline                 |
| `tempo.yml`            | Trace backend                           |
| `datasources.yml`      | Grafana datasource provisioning         |
| `docker-compose.yml`   | 整套 Lab runtime                        |
| `Makefile`             | 常用操作入口                            |

這樣拆分，是為了讓未來修改：

```text
Metrics
Logs
Tracing
Runtime
```

時，不必全部塞進同一個檔案裡尋寶。

---

# ⑦ 安裝今天需要的 Python Dependencies

Day 0 已經統一使用：

```text
uv
+
pyproject.toml
```

直接執行：

```bash
uv add \
  fastapi \
  "uvicorn[standard]" \
  pydantic-settings \
  prometheus-client \
  python-json-logger \
  opentelemetry-api \
  opentelemetry-sdk \
  opentelemetry-exporter-otlp-proto-grpc \
  opentelemetry-instrumentation-fastapi
```

接著：

```bash
uv sync
```

今天我們刻意使用 Prometheus 官方 Python client。

因為接下來會自己理解：

```text
Counter
Gauge
Histogram
Labels
```

而不是第一天就讓 instrumentation library 幫我們全部藏起來。

Prometheus 官方 client 本身就提供 Counter、Gauge、Histogram 等 metric type；其中 Histogram 特別適合 request latency，之後可以用 bucket 計算 P95、P99。

---

# ⑧ 建立第一個 FastAPI Service

我們今天需要四個 endpoint：

```text
GET /health
GET /ready
GET /api/demo
GET /metrics
```

其中前三個各有不同用途。

---

# `/health`：你還活著嗎？

建立：

```python
@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
    }
```

它回答：

> Process 是否還正常運作？

注意：

今天的 `/health` **不要去檢查 PostgreSQL。**

也不要檢查：

```text
Redis
Gemini
External API
```

為什麼？

假設：

```text
FastAPI    alive
PostgreSQL down
```

如果你的 Liveness Check 因為 PostgreSQL down 就失敗：

```text
Kubernetes / orchestrator
       ↓
Restart FastAPI
       ↓
PostgreSQL still down
       ↓
Restart FastAPI
       ↓
PostgreSQL still down
       ↓
Restart FastAPI
```

你得到的不是修復。

你得到：

> 一個很有毅力的 Restart Loop。

---

# `/ready`：你現在能接客嗎？

Readiness 回答的是：

> 這個 instance 現在適合接受使用者流量嗎？

Day 2 先保持：

```python
@app.get("/ready")
async def ready() -> dict[str, str]:
    return {
        "status": "ready",
    }
```

之後我們再開始實驗：

```text
DB down 時 readiness 要不要失敗？
Redis down 呢？
LLM provider down 呢？
Fallback 還能工作呢？
```

這些沒有永遠正確的答案。

這些取決於：

```text
Critical Path
Failure Mode
Degradation Strategy
```

後面再談。

---

# ⑨ 建立我們的實驗白老鼠 `/api/demo`

接下來是整個系列很重要的 endpoint：

```text
/api/demo
```

它未來會被我們：

```text
延遲
打爆
timeout
return 500
加 dependency
加 retry
加 fallback
```

今天先讓它支援：

```text
delay_ms
fail
```

例如：

```text
GET /api/demo
```

正常。

```text
GET /api/demo?delay_ms=500
```

故意慢 500 ms。

```text
GET /api/demo?fail=true
```

故意 500。

你可能會想：

> Day 3 才是 Failure Injection，為什麼今天先留這兩個？

因為：

> **設計一個 Lab 時，要先替未來的實驗留下控制點。**

---

## 基本 Endpoint

```python
import asyncio
from datetime import UTC, datetime

from fastapi import HTTPException


@app.get("/api/demo")
async def demo(
    delay_ms: int = 0,
    fail: bool = False,
) -> dict[str, str]:

    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    if fail:
        raise HTTPException(
            status_code=500,
            detail="Injected failure",
        )

    return {
        "message": "SRE Lab is running",
        "timestamp": datetime.now(UTC).isoformat(),
    }
```

現在我們已經擁有：

```text
Normal Request
Slow Request
Failed Request
```

接下來就開始替它裝感測器。

---

# ⑩ Metrics：先讓我們看見趨勢

今天先收集三個最基本的 HTTP Metrics：

```text
http_requests_total
http_request_duration_seconds
http_requests_in_progress
```

它們分別是：

### Counter

```text
http_requests_total
```

回答：

> 到目前總共處理多少 requests？

Counter 只會增加。

Prometheus Python client 在 exposition 時也會按照慣例暴露 `_total` suffix。

---

### Histogram

```text
http_request_duration_seconds
```

回答：

> Request latency 分布如何？

單一的平均值不夠：

```text
average = 320 ms
```

我們會把 observations 放進：

```text
<= 0.1s
<= 0.25s
<= 0.5s
<= 1s
<= 2.5s
...
```

後面 Day 16，我們才能開始計算：

```text
P50
P95
P99
```

---

### Gauge

```text
http_requests_in_progress
```

回答：

> 現在同時有多少 Requests 還在執行？

Gauge 和 Counter 不一樣。

它可以：

```text
+1
-1
```

所以適合：

```text
Active requests
Queue depth
Open connections
```

Prometheus 官方 client 也是這樣定義 Gauge 的使用情境。

---

# ⑪ Metric Labels 不要亂塞

我們讓 metric 帶：

```text
method
route
status_code
```

例如：

```text
http_requests_total{
  method="GET",
  route="/api/demo",
  status_code="200"
}
```

注意這裡使用：

```text
route="/api/demo"
```

而不是：

```text
path="/users/12345678"
```

假設你有：

```text
/users/1
/users/2
/users/3
...
/users/10000000
```

然後全部變 metric labels。

Congratulations。

你剛剛建立了：

# Cardinality Generator 3000

Metrics 的 Label Value 應該保持有限集合。

例如：

```text
route
method
status_code
```

不要塞：

```text
user_id
request_id
email
full URL
query string
prompt
```

這些資訊比較適合：

```text
Logs
Traces
```

Honeycomb 的 Charity Majors 在 [Metrics: Not the Observability Droids You're Looking For](https://www.honeycomb.io/blog/metrics-not-the-observability-droids-youre-looking-for) 裡提到過真實案例：某些團隊因為把高基數欄位塞進 metric label，時序資料庫的 cardinality 直接爆炸，每月監控帳單多出數萬美元。這不是危言聳聽，是 time series 資料庫的儲存結構決定的——每多一種 label 組合，就是一條新的 time series。

---

# ⑫ 實作 Prometheus Metrics Middleware

`app/metrics.py`：

```python
from prometheus_client import Counter, Gauge, Histogram


HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    [
        "method",
        "route",
        "status_code",
    ],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    [
        "method",
        "route",
    ],
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    [
        "method",
        "route",
    ],
)
```

在 `main.py` 加 middleware：

```python
import time

from fastapi import Request

from app.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
)


@app.middleware("http")
async def metrics_middleware(
    request: Request,
    call_next,
):
    route = request.url.path
    method = request.method

    HTTP_REQUESTS_IN_PROGRESS.labels(
        method=method,
        route=route,
    ).inc()

    started_at = time.perf_counter()

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response

    except Exception:
        status_code = 500
        raise

    finally:
        duration = time.perf_counter() - started_at

        HTTP_REQUESTS_IN_PROGRESS.labels(
            method=method,
            route=route,
        ).dec()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method,
            route=route,
        ).observe(duration)

        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            route=route,
            status_code=str(status_code),
        ).inc()
```

先不用追求完美。

後面我們還會處理：

```text
Route template
404
Exception handling
Excluded paths
Health endpoint
Metrics endpoint
```

今天先確保：

> Request 發生時，我們真的可以量到它。

---

# ⑬ 暴露 `/metrics`

Prometheus Python client 官方支援直接建立 ASGI metrics application。

```python
from prometheus_client import make_asgi_app


metrics_app = make_asgi_app()

app.mount(
    "/metrics",
    metrics_app,
)
```

啟動 FastAPI 後：

```bash
curl http://localhost:8000/metrics/
```

應該可以看到：

```text
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter

http_requests_total{
  method="GET",
  route="/api/demo",
  status_code="200"
} 5
```

以及：

```text
http_request_duration_seconds_bucket
http_request_duration_seconds_sum
http_request_duration_seconds_count
```

如果看到這些：

第一個感測器完成。

---

# ⑭ Prometheus 怎麼知道要抓誰？

建立：

```text
observability/prometheus/prometheus.yml
```

```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: "sre-lab-api"

    metrics_path: /metrics/

    static_configs:
      - targets:
          - api:8000
```

注意：

Docker Compose 裡：

```text
localhost
```

不是另一個 container。

Prometheus 要找到 FastAPI：

```text
api:8000
```

這裡的：

```text
api
```

就是 Docker Compose service name。

---

# ⑮ 第一個 PromQL

先送幾個 request：

```bash
curl http://localhost:8000/api/demo
curl http://localhost:8000/api/demo
curl "http://localhost:8000/api/demo?fail=true"
```

然後查：

```promql
sum(rate(http_requests_total[5m]))
```

大概代表：

> 最近五分鐘，每秒平均收到多少 Request。

再查：

```promql
sum(
  rate(
    http_requests_total{
      status_code=~"5.."
    }[5m]
  )
)
/
sum(
  rate(
    http_requests_total[5m]
  )
)
```

代表：

```text
5xx Request Rate
────────────────
All Requests
```

也就是最原始版本的：

# Error Rate

注意：

今天不要急著宣布：

```text
我們已經有 Availability SLI！
```

還沒。

因為未來會出現很多問題：

```text
4xx 算失敗嗎？
/health 算 user traffic 嗎？
bot request 算嗎？
malformed request 算嗎？
dependency failure 怎麼算？
```

Day 14 之後再正式處理。

今天只是：

> **先收集未來需要的 Evidence。**

---

# ⑯ Logs：`request failed` 幾乎等於沒說

我們接著處理 Logs。

最沒用的 log 大概長這樣：

```text
ERROR request failed
```

謝謝。

所以：

```text
哪個 request？
哪個 route？
多久？
什麼 status？
哪個 instance？
哪條 trace？
```

不知道。

今天直接使用：

# Structured JSON Logging

理想 log：

```json
{
  "timestamp": "2026-08-27T12:00:00Z",
  "level": "INFO",
  "message": "request completed",
  "service": "api",
  "request_id": "c5448813",
  "method": "GET",
  "path": "/api/demo",
  "status_code": 200,
  "duration_ms": 123.4
}
```

這樣 Loki 才可以真正：

```text
Filter
Parse
Search
Correlate
```

而不是在一坨文字裡考古。

---

# ⑰ Request ID

每個 Request 先產生：

```text
request_id
```

Middleware：

```python
from uuid import uuid4

from fastapi import Request


@app.middleware("http")
async def request_context_middleware(
    request: Request,
    call_next,
):
    request_id = request.headers.get(
        "X-Request-ID",
        str(uuid4()),
    )

    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response
```

現在 Request：

```text
GET /api/demo
```

就可以有自己的：

```text
Request ID
```

例如：

```text
9a8ce214-fac1-43e9-b533-...
```

未來 Incident Investigation 時：

```text
Customer:
「17:31 那次 request 失敗了。」

Engineer:
「有 Request ID 嗎？」
```

這句話的含金量會突然非常高。

---

# ⑱ Structured Log 裡該放什麼？

今天至少記：

```text
timestamp
level
message
service
request_id
method
path
status_code
duration_ms
```

後面還會增加：

```text
trace_id
span_id
deployment_version
environment
dependency
retry_count
```

AI 時代可能再增加：

```text
provider
model
prompt_version
retrieval_status
tool_name
evaluation_result
```

先踩一下煞車。

**Logs 不是垃圾場。**

不要直接記：

```text
Password
Authorization header
API key
Credit card
Personal data
Raw access token
```

到了 LLM 更麻煩。

因為以下內容也可能包含敏感資訊：

```text
Prompt
Retrieved documents
Tool input
Tool output
Conversation history
```

所以：

> 「Observability 要多記資料」

不等於：

> 「把所有東西都 Dump 到 Loki。」

---

# ⑲ Docker Logs → Alloy → Loki

Application 只要：

```text
stdout
```

輸出 JSON。

Docker 會保留 container logs。

Alloy 負責：

```text
Discover Docker
       ↓
Read Container Logs
       ↓
Attach Labels
       ↓
Send to Loki
```

Grafana 官方現在也提供 `discovery.docker` 與 `loki.source.docker` 來完成這種 Docker log pipeline。

概念上的 Alloy config：

```text
discovery.docker
      ↓
loki.source.docker
      ↓
loki.write
      ↓
Loki
```

例如：

```alloy
discovery.docker "containers" {
  host = "unix:///var/run/docker.sock"
}

loki.source.docker "containers" {
  host       = "unix:///var/run/docker.sock"
  targets    = discovery.docker.containers.targets
  forward_to = [loki.write.local.receiver]
}

loki.write "local" {
  endpoint {
    url = "http://loki:3100/loki/api/v1/push"
  }
}
```

這就是今天整條：

```text
FastAPI
 ↓
stdout
 ↓
Docker
 ↓
Alloy
 ↓
Loki
```

---

# ⑳ 在 Grafana 查 Log

Grafana Explore 選 Loki。

先查：

```logql
{service="api"}
```

如果今天 label 還沒有整理完整，也可以先從 container label 查起。

接著找 error：

```logql
{service="api"} |= "ERROR"
```

真正上 Production 後，我們還會進一步 parse JSON：

```text
status_code
duration_ms
request_id
```

但 Day 2 的目標很單純：

> **我打了一次 `/api/demo`，Grafana 裡真的能找到它留下的 log。**

---

# ㉑ Trace：第三種視角

到這裡我們已經有：

```text
Metrics
Logs
```

現在加入：

```text
Trace
```

如果只看 Metrics：

```text
P95 latency ↑
```

你知道：

> 變慢了。

如果看 Logs：

```text
request completed
duration_ms=5201
```

你知道：

> 這次 Request 很慢。

但 Trace 想回答的是：

> **到底慢在哪一段？**

今天只有 FastAPI，所以很簡單：

```text
GET /api/demo
```

未來它會變成：

```text
POST /ask
│
├── PostgreSQL
├── Redis
├── Retrieval
├── Vector DB
├── Gemini
├── Tool
└── Validator
```

這就是我們 Day 1 已經偷看過一次的世界。

只不過今天改用：

# OpenTelemetry

---

# ㉒ 初始化 OpenTelemetry

`app/telemetry.py`：

```python
from opentelemetry import trace

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)

from opentelemetry.sdk.resources import (
    SERVICE_NAME,
    Resource,
)

from opentelemetry.sdk.trace import (
    TracerProvider,
)

from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)


def configure_tracing() -> None:
    resource = Resource.create(
        {
            SERVICE_NAME: "sre-lab-api",
        }
    )

    provider = TracerProvider(
        resource=resource,
    )

    exporter = OTLPSpanExporter(
        endpoint="otel-collector:4317",
        insecure=True,
    )

    provider.add_span_processor(
        BatchSpanProcessor(
            exporter,
        )
    )

    trace.set_tracer_provider(
        provider,
    )
```

然後 FastAPI instrumentation：

```python
from opentelemetry.instrumentation.fastapi import (
    FastAPIInstrumentor,
)


configure_tracing()

app = FastAPI()

FastAPIInstrumentor.instrument_app(
    app,
)
```

現在：

```text
GET /api/demo
```

每次 Request 都會自動建立 HTTP server span。

OpenTelemetry Python 的 Trace 與 Metrics 已屬 stable；OTLP 也是官方建議和 Collector 溝通的主要方式。

---

# ㉓ Trace 的資料到底去哪裡？

Application：

```text
FastAPI
```

它不直接寫入：

```text
Tempo
```

資料會先經過：

```text
FastAPI
   │
   │ OTLP/gRPC
   ▼
OpenTelemetry Collector
   │
   │ OTLP/gRPC
   ▼
Tempo
```

Collector config：

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:

exporters:
  otlp/tempo:
    endpoint: tempo:4317

    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers:
        - otlp

      processors:
        - batch

      exporters:
        - otlp/tempo
```

這個架構跟 Grafana 官方 Tempo 文件建議的 Collector pipeline 相同：

```text
Receiver
 ↓
Processor
 ↓
Exporter
 ↓
Tempo
```

---

# ㉔ 為什麼中間還要 Collector？

可能有人會問：

> FastAPI 不能直接送 Tempo 嗎？

可以。

但加入 Collector 有幾個很重要的理由。

Application 可以永遠只說：

```text
Send OTLP here.
```

Collector 再決定：

```text
Sampling
Batching
Filtering
Enrichment
Routing
Retry
Multiple exporters
```

未來甚至：

```text
                 ┌→ Tempo
Application → OTel Collector
                 └→ Vendor B
```

Application 不必知道。

這就是：

> **把 Observability transport policy 從 Application Code 抽離。**

這個 Lab 還小。

但我們先保留正確的 Architecture Boundary。

---

# ㉕ Tempo 才是我們查看 Trace 的地方

Tempo 啟動後：

```text
OpenTelemetry Collector
        ↓
      Tempo
```

Tempo 負責：

```text
Store
Search
Retrieve
```

Grafana 再把 Tempo 設成 datasource。

```text
Grafana
  ├── Prometheus
  ├── Loki
  └── Tempo
```

一個 UI 裡看到：

```text
Metrics
Logs
Traces
```

我們的 Observability Lab 終於開始有樣子了。

---

# ㉖ Metrics、Logs、Traces 到底差在哪？

這張表今天請記起來。

| Telemetry | 最擅長回答                  |
| --------- | --------------------------- |
| Metrics   | 系統整體發生什麼趨勢？      |
| Logs      | 某個事件具體發生什麼？      |
| Traces    | 某次 Request 經過哪些步驟？ |

例如：

```text
Users 說服務變慢。
```

### Metrics

看到：

```text
P95
200 ms → 4.8 s
```

告訴你：

> 確實變慢。

### Logs

找到：

```json
{
  "request_id": "abc",
  "duration_ms": 5120
}
```

告訴你：

> 這個 Request 真的花了五秒。

### Trace

看到：

```text
GET /api/demo      5.12s
└── dependency     5.01s
```

告訴你：

> 時間花在哪。

調查時要把它們合起來看：

```text
Metrics
   +
Logs
   +
Traces
```

---

# ㉗ Request ID、Trace ID 又是什麼關係？

Request ID 是：

```text
Application-defined correlation ID
```

Trace ID 則來自：

```text
Distributed Tracing Context
```

兩個可以一起存在。

例如：

```json
{
  "request_id": "req-123",
  "trace_id": "9940c...",
  "span_id": "ac91...",
  "message": "request completed"
}
```

OpenTelemetry 本身也特別定義了透過：

```text
TraceId
SpanId
```

把 logs 與 traces 關聯起來的方式。

所以未來 Investigation 可以做到：

```text
Customer reports Request ID
        ↓
Find Log
        ↓
Get Trace ID
        ↓
Open Trace
        ↓
Find Slow Dependency
```

做到這裡，Investigation 才有：

# Correlation

---

# ㉘ Docker Compose：把所有東西組起來

今天 Compose 至少包含：

```text
api
postgres
redis
prometheus
grafana
loki
alloy
otel-collector
tempo
```

概念：

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"

  postgres:
    image: postgres

  redis:
    image: redis

  prometheus:
    image: prom/prometheus

  grafana:
    image: grafana/grafana

  loki:
    image: grafana/loki

  alloy:
    image: grafana/alloy

  otel-collector:
    image: otel/opentelemetry-collector-contrib

  tempo:
    image: grafana/tempo
```

完整版本還需要：

```text
ports
volumes
environment
healthchecks
commands
configs
networks
```

但先理解一件事情：

這些 Service 全部都在同一個 Docker Network 裡。

在這個 network 裡：

```text
api:8000
prometheus:9090
loki:3100
tempo:4317
otel-collector:4317
redis:6379
postgres:5432
```

可以直接透過：

```text
service name
```

互相找到。

---

# ㉙ 啟動 SRE Lab

第一次：

```bash
docker compose up -d --build
```

然後：

```bash
docker compose ps
```

你希望看到：

```text
api
postgres
redis
prometheus
grafana
loki
alloy
otel-collector
tempo
```

都在：

```text
running
```

如果想看全部 log：

```bash
docker compose logs -f
```

只看 API：

```bash
docker compose logs -f api
```

---

# ㉚ 第一輪 Smoke Test

先測：

```bash
curl http://localhost:8000/health
```

期待：

```json
{
  "status": "ok"
}
```

再：

```bash
curl http://localhost:8000/ready
```

期待：

```json
{
  "status": "ready"
}
```

接著：

```bash
curl http://localhost:8000/api/demo
```

應該得到：

```json
{
  "message": "SRE Lab is running",
  "timestamp": "..."
}
```

---

# ㉛ 現在故意慢一點

```bash
curl \
  "http://localhost:8000/api/demo?delay_ms=1000"
```

這次應該約：

```text
1 second
```

到 Prometheus 查：

```promql
http_request_duration_seconds_count
```

以及：

```promql
http_request_duration_seconds_bucket
```

我們今天還不分析 P95。

但你已經可以看到：

> Terminal 只顯示一次 latency；Prometheus 會把它持續累積成可查詢的 telemetry。

---

# ㉜ 再故意失敗一次

```bash
curl \
  "http://localhost:8000/api/demo?fail=true"
```

期待：

```text
HTTP 500
```

現在我們有三個地方可以查。

### Prometheus

```promql
http_requests_total{
  status_code="500"
}
```

### Loki

搜尋：

```text
Injected failure
```

或：

```text
status_code=500
```

### Tempo

找到這次：

```text
GET /api/demo
```

查看：

```text
HTTP status
Duration
Trace ID
```

同一個 Failure：

```text
Metrics
Logs
Traces
```

會留下三種不同的證據。

這就是今天真正要建立的直覺。

---

# ㉝ Grafana 是調查入口

很多人第一次碰 Grafana，會把目標放在：

> 做一個很酷的 Dashboard。

今天先不要。

Grafana 今天只是：

# Unified Investigation Interface

Datasource：

```text
Prometheus
Loki
Tempo
```

我們先確定：

```text
Grafana
├── Metrics 查得到
├── Logs 查得到
└── Traces 查得到
```

Dashboard 美化後面再做。

SRE 的世界裡：

> 一張醜但能回答問題的 Dashboard，通常比一張超漂亮但不知道要看什麼的 Dashboard 有價值。

---

# ㉞ PostgreSQL 和 Redis 今天為什麼還要放進來？

幾乎沒有外部 Dependency。

這種服務：

> 太健康了。

不好玩。

未來我們會開始建立：

```text
FastAPI
 ├── PostgreSQL
 └── Redis
```

然後：

```bash
docker compose stop postgres
```

接著觀察：

```text
API 怎麼壞？
Readiness 怎麼變？
Latency 怎麼變？
Log 留下什麼？
Trace 卡在哪？
```

Redis 也一樣。

所以今天先把：

```text
Dependency topology
```

建立起來。

不用急著寫功能。

---

# ㉟ 為什麼不直接 Kubernetes？

因為現在 Kubernetes 只會增加：

```text
Deployment
Service
ConfigMap
Secret
Ingress
PVC
Probe
Helm
RBAC
Networking
```

而我們現在真正要學的是：

```text
Reliability
Observability
Failure
```

Docker Compose 的優勢是：

```text
低成本
快速重建
本機執行
容易故意停服務
```

等我們真的需要：

```text
Replica
Rolling Deployment
Autoscaling
Pod eviction
Probe
Scheduling
```

時，再進 Kubernetes。

不要因為學 SRE：

> 第一天就先召喚 Kubernetes。

---

# ㊱ Makefile：把操作方式固定下來

我們可以建立：

```makefile
.PHONY: up down reset logs ps

up:
	docker compose up -d --build

down:
	docker compose down

reset:
	docker compose down -v
	docker compose up -d --build

logs:
	docker compose logs -f

ps:
	docker compose ps
```

之後只要：

```bash
make up
```

停止：

```bash
make down
```

完整重建：

```bash
make reset
```

這看起來非常小。

這也是 Reliability 的一部分：

> **把正確操作變得簡單、固定、可重複。**

---

# ㊲ `docker compose down` 和 `down -v` 差很多

正常停止：

```bash
docker compose down
```

通常保留 named volumes。

但：

```bash
docker compose down -v
```

會把 volumes 一起刪除。

包括可能存在裡面的：

```text
PostgreSQL data
Grafana data
Prometheus data
Loki data
Tempo data
```

所以：

```text
down
```

比較像：

> 關機。

而：

```text
down -v
```

更接近：

> 恢復原廠設定。

Lab 隨便 reset 沒關係。

Production 這樣按：

> 下一篇可能就直接變 Incident Postmortem。

---

# ㊳ Day 2 的最低驗收標準

今天不要求：

```text
完美 Dashboard
SLI
SLO
Alert
Tracing Sampling Policy
Production Storage
HA
TLS
Authentication
```

只要求這些。

- [ ] `docker compose up -d --build` 成功
- [ ] `/health` 回傳 200
- [ ] `/ready` 回傳 200
- [ ] `/api/demo` 正常回傳
- [ ] `/api/demo?delay_ms=500` 可以產生延遲
- [ ] `/api/demo?fail=true` 可以產生 500
- [ ] Prometheus 成功 scrape `/metrics`
- [ ] `http_requests_total` 有資料
- [ ] `http_request_duration_seconds` 有資料
- [ ] FastAPI 輸出 JSON structured logs
- [ ] Alloy 能收集 Docker logs
- [ ] Loki 可以查到 API log
- [ ] 每個 Request 都有 Request ID
- [ ] FastAPI trace 能送到 OTel Collector
- [ ] OTel Collector 能送到 Tempo
- [ ] Grafana 可以查 Prometheus
- [ ] Grafana 可以查 Loki
- [ ] Grafana 可以查 Tempo
- [ ] 環境可以停止並重新建立

全部打勾後，SRE Lab v0.1 完成。

---

# ㊴ 今天還沒有做 SLO

今天我們擁有：

```text
Requests
Errors
Latency
Logs
Traces
```

但這些：

> **只是 Telemetry。**

Telemetry 告訴我們：

```text
發生什麼。
```

Reliability Engineering 接下來還要回答：

```text
什麼叫做好？
什麼叫做壞？
什麼程度可以接受？
什麼程度應該 Alert？
```

也就是之後會進入：

```text
SLI
SLO
Error Budget
Alerting
Incident Response
```

所以不要看到：

```text
Prometheus + Grafana
```

就宣布：

> 我們完成 Observability 了。

更不要宣布：

> 我們完成 SRE 了。

我們只是終於：

# 有眼睛了。

---

# ㊵ AI Era Extension：為什麼 Day 2 先不碰 AI？

這個 Lab 今天看起來還是一個普通 Web Service：

```text
FastAPI
├── PostgreSQL
├── Redis
└── Observability
```

這是故意的。

因為後面 AI 系統會逐步變成：

```text
Client
 ↓
FastAPI
 ↓
Prompt
 ↓
Retriever
 ↓
Vector DB
 ↓
Model
 ↓
Tool
 ↓
Validator
 ↓
Response
```

如果連：

```text
HTTP latency
Request ID
Structured logs
Trace context
Dependency failure
```

都還沒處理好，

直接加入：

```text
Agent
RAG
Tool Calling
```

你得到的只會是：

# 更高級的黑盒子。

所以這套系列會照這個順序走。

---

## Day 02

```text
FastAPI
PostgreSQL
Redis
Metrics
Logs
Traces
```

---

## Day 12

加入：

```text
External Mock Service
```

開始模擬 Dependency Failure。

---

## Day 18

加入 AI-specific SLI：

```text
TTFT
Token Usage
Queue Delay
Model Latency
Tool Success
```

---

## Day 19

加入：

```text
Golden Dataset
Task Success
Evaluation
```

開始面對：

```text
HTTP 200
≠
Correct Answer
```

---

## Day 23

Trace 會從：

```text
HTTP Request
```

真正長成：

```text
Request
├── Prompt
├── Retrieval
├── Model
├── Tool
└── Validation
```

---

## Day 26

Alert 也會增加：

```text
Provider outage
Queue backlog
Tool failure
Model unavailable
```

---

## Day 29

最後加入：

```text
Timeout
Retry
Backoff
Circuit Breaker
Fallback Provider
Graceful Degradation
```

這時候 Day 2 建的 Lab 才會真正變成：

# AI Reliability Lab

---

# ㊶ Day 2 的重點

今天表面上安裝了很多東西：

```text
FastAPI
Prometheus
Grafana
Loki
Alloy
Tempo
OpenTelemetry Collector
PostgreSQL
Redis
```

但這些名字不是重點。

今天建立的是三個 Observability 問題：

```text
Metrics
→ 系統整體發生什麼？

Logs
→ 某個事件到底發生什麼？

Traces
→ 某次 Request 經過什麼？
```

工程原則很簡單：

> **先讓系統可觀測，再讓系統變複雜。**

如果未來一個 RAG 或 Agent 上 Production 前，連：

```text
Request ID
Metrics
Structured Logs
Trace
Version
Failure Record
```

都沒有，

那當它開始回答：

```text
「我覺得應該是這樣。」
```

值班工程師大概也只能回答：

```text
「我也覺得問題應該在那裡。」
```

那就不是 Reliability Engineering，只是大型多人通靈現場。
![通靈](https://memeprod.sgp1.digitaloceanspaces.com/user-wtf/1645769868951.jpg)

---

# Production Takeaway

今天的 SRE Lab 不是 Production Architecture Template。

例如我們目前沒有處理：

```text
High Availability
Authentication
TLS
Backup
Long-term retention
Remote storage
Multi-tenancy
Sampling strategy
Secret management platform
Resource limits
Kubernetes
```

Grafana 官方也指出，Docker Compose 版本 Loki 比較適合 evaluation、testing 與 development；Production deployment 另有要求。

這份 Lab 的目標是驗證 Reliability Hypothesis，不是複製 Production 的服務規模。

例如：

```text
Hypothesis:
PostgreSQL timeout 會提高 API P95 latency。

Experiment:
故意讓 PostgreSQL slowdown。

Evidence:
Prometheus latency histogram
+
Loki error log
+
Tempo trace

Conclusion:
判斷 Failure 如何傳遞。
```

這就是接下來的學習方式。

裝好 Prometheus、Grafana、Loki、Tempo，離「做完 SRE」還很遠。[Google SRE Book — Service Level Objectives](https://sre.google/sre-book/service-level-objectives/) 講的下一步才是重點：先定義使用者真正在乎什麼、訂出 SLI/SLO，再回頭看 telemetry 有沒有回答到那個問題。我們今天只是先把「能收集證據」這件事做好，還沒有回答「這些證據要拿來做什麼決策」。

---

# 參考資料

- [Dean & Barroso：The Tail at Scale](https://www.barroso.org/publications/TheTailAtScale.pdf)
- [USENIX：Metastable Failures in the Wild](https://www.usenix.org/publications/loginonline/metastable-failures-wild)
- [Honeycomb：Metrics: Not the Observability Droids You're Looking For](https://www.honeycomb.io/blog/metrics-not-the-observability-droids-youre-looking-for)
- [Google SRE Book：Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)

---

# 下一篇：Day 03｜主動把服務弄壞

現在我們終於有：

```text
Metrics
Logs
Traces
```

如果服務永遠正常，

那這三個東西看起來非常無聊。

所以 Day 3 開始：

# Breaking Things.

我們會主動製造：

```text
HTTP 500
Timeout
Dependency unavailable
Container crash
Resource pressure
```

然後觀察同一個 Failure 在：

```text
Metrics
Logs
Traces
```

分別留下什麼訊號。

第一次真正實踐：

```text
Build
 ↓
Break
 ↓
Observe
 ↓
Explain
```

並開始回答一個非常 SRE 的問題：

> **當使用者只告訴你「系統壞了」，你能不能靠 Evidence，把未知數一個一個消掉？**

---

> **Learning SRE for the AI Era**
>
> Day 1，我們打開了一次 AI Workflow。
>
> Day 2，我們替整個系列建立共同的 Observability Foundation。
>
> 從下一篇開始，我們終於可以放心地：
>
> **把它弄壞。**
> ![啊罵賣掉](https://megapx-assets.dcard.tw/images/2c91c7b1-b5c8-42dd-9c1a-7285100a8db6/1280.jpeg)
>
> **Build → Trace → Break → Measure → Evaluate → Recover → Improve.**
