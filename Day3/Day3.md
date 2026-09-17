# Day 03｜為什麼學 SRE 必須主動製造故障？

> GitHub：[darkstar1227/learning-sre-for-ai-era](https://github.com/darkstar1227/learning-sre-for-ai-era)

**英文標題：**  
*Why You Need to Break Systems to Learn SRE*

**系列定位：**  
Learning SRE for the AI Era — Day 03

**一句話摘要：**  
主動讓 FastAPI 變慢、回傳 500、失去 PostgreSQL、被強制終止，甚至耗盡記憶體，再從使用者、Metrics、Logs 與 Traces 四個角度拼回故障現場。

---

昨天，我們建立了一套看起來很健康的 SRE Lab：

```text
Client
  ↓
FastAPI
  ├── Prometheus
  ├── Alloy → Loki
  └── OpenTelemetry Collector → Tempo
```

`docker compose ps` 顯示 `Up`。

`/health` 回傳 `200`。

Grafana 也有資料。

一切看起來都很正常。

所以今天要做一件事：

## **把它弄壞。**

![小女孩微笑爆炸](https://v3-statics.mirrormedia.mg/images/20210430173353-f8ab123b775f2a0c5ef8ea644a50c0ac-w2400.jpg)

好吧，有些工程師可能真的喜歡破壞。原因很直接：

> **你無法只靠正常狀態，驗證系統是否真的可觀測、可診斷、可恢復。**

今天會處理五類故障情境，其中 Memory Exhaustion 是可選實驗：

1. Slow request
2. Client timeout
3. HTTP 500
4. PostgreSQL unavailable
5. Container crash 與 memory exhaustion

每一次都遵循同一個循環：

```text
Baseline
   ↓
Inject Failure
   ↓
Observe User Impact
   ↓
Collect Evidence
   ↓
Recover
   ↓
Verify Recovery
```

這就是接下來 30 天會反覆使用的：

# Build → Break → Observe → Explain

---

# ① 今天不是 Chaos Engineering

先把界線畫清楚。

2008 年 8 月，Netflix 發生資料庫損毀，DVD 寄送服務中斷三天。之後 Netflix 展開長達七年的雲端遷移，架構也從資料中心的垂直擴展與單點故障，逐步轉向 AWS 上的水平擴展與分散式系統。

但換架構不代表故障從此消失。

2010 年，Netflix 建立 Chaos Monkey，在營業時間隨機關閉 production instance，讓工程師在場時驗證服務能否優雅降級。2011 年，它又擴充成 Simian Army；其中 Chaos Gorilla 會模擬整個 Availability Zone 故障。

Netflix 主動把容錯驗收排進日常，不等下一場事故代勞。

參考：[Netflix 雲端遷移回顧](https://about.netflix.com/en/news/completing-the-netflix-cloud-migration)、[The Netflix Simian Army](https://netflixtechblog.com/the-netflix-simian-army-16e57fbab116)

今天的 Lab 沒有 production traffic，也沒有猴子軍團。

今天做的是：

```text
Controlled Failure Injection
```

我們已經知道：

* 要破壞哪個元件。
* 何時開始破壞。
* 預期造成什麼影響。
* 如何停止實驗。
* 如何恢復服務。

Day 30 會再加入本文目前尚未涵蓋的 Chaos Engineering 實務項目：

```text
Steady-state hypothesis
Blast radius control
Abort condition
Automated experiment
Learning review
```

今天的目標比較單純：

> **讓故障變成可以親眼觀察、動手記錄的證據。**

所有操作都只應在 Day 2 建立的本機 Lab 或隔離測試環境執行。

---

# ② 先預習三個詞：Fault、Error、Failure

這三個詞會在 Day 10 正式展開，今天先用一個例子區分它們。

```text
PostgreSQL container 被停止
            ↓
FastAPI 無法建立 DB connection
            ↓
使用者收到 HTTP 503
```

| 層次 | 本次實驗中的例子 |
| --- | --- |
| **Fault** | PostgreSQL 被停止 |
| **Error** | Application 內部出現 connection error |
| **Failure** | API 無法完成使用者要求，回傳 503 |

Fault 不一定立刻變成使用者看得見的 Failure。

例如 Redis 掛掉，但這條 Request 根本沒用到 Redis：

```text
Fault exists
User impact = 0
```

反過來也一樣。

使用者看到「很慢」，系統卻沒有任何 5xx：

```text
Error rate = 0%
User patience = 0%
```

所以我們不能只問：

> 有沒有 Error？

還要問：

> 使用者的 Critical Path 有沒有失敗？

---

# ③ 2026 年套件與工具查核

本文撰寫前，先依 **2026-09-08** 的官方文件檢查 Day 0～Day 3 使用的工具。

| 項目 | 本系列採用 | 查核結果 |
| --- | --- | --- |
| Python 套件管理 | `uv`、`pyproject.toml`、`uv.lock` | 持續維護；`uv sync` 會依 lockfile 同步環境 |
| Gemini SDK | `google-genai` | Google 現行 GA SDK |
| 舊 Gemini SDK | `google-generativeai` | 已停止支援，不使用 |
| Docker Compose | `docker compose` | Compose V2 現行語法 |
| 舊 Compose CLI | `docker-compose` | Compose V1 已停止維護，不使用 |
| Log collector | Grafana Alloy | 現行方案 |
| Promtail | 不使用 | 2026-03-02 EOL |
| Grafana Agent | 不使用 | 2025-11-01 EOL |
| PostgreSQL driver | `psycopg` 3 | Psycopg 現行世代，支援 asyncio |
| Prometheus client | `prometheus-client` | 官方 Python client，持續維護 |
| Tracing | OpenTelemetry Python + OTLP | Trace API/SDK 為 stable；使用 Collector 與 Tempo |

這裡還有一個容易被忽略的風險。

Day 2 的 Compose 範例使用：

```yaml
image: grafana/grafana
```

沒有 tag 時等同使用浮動版本。

今天能跑，不代表三個月後重新 pull 還是同一套 bits。

教學文字可以用簡化名稱；真正提交到 Repository 時，應將已驗證的 image tag 或 digest 寫死，並提交：

```text
pyproject.toml
uv.lock
docker-compose.yml
```

可以先列出目前使用的 image：

```bash
docker compose config --images
docker images --digests
```

如果修改過 Python dependencies，使用：

```bash
uv lock
uv sync --locked
```

`--locked` 會在專案設定與 `uv.lock` 不一致時失敗，避免工具在你沒注意時重新解依賴。

本文沒有加入已停止維護的套件。

參考資料：

* [Google：Gemini API libraries](https://ai.google.dev/gemini-api/docs/libraries)
* [Docker：Compose](https://docs.docker.com/compose/)
* [Docker：retired products and features](https://docs.docker.com/retired/)
* [Grafana：Promtail](https://grafana.com/docs/loki/latest/send-data/promtail/)
* [Grafana：Grafana Agent](https://grafana.com/docs/agent/latest/)
* [Grafana：Send log data to Loki](https://grafana.com/docs/loki/latest/send-data/)
* [Psycopg 3 documentation](https://www.psycopg.org/psycopg3/docs/)
* [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
* [Prometheus Python client](https://prometheus.github.io/client_python/)

---

# ④ 今天要留下什麼 Evidence？

同一個故障，要同時從四個角度看。

| 視角 | 問題 | 工具 |
| --- | --- | --- |
| User | 使用者看到慢、錯誤，還是完全連不上？ | `curl` |
| Metrics | 影響多大？何時開始？趨勢如何？ | Prometheus / Grafana |
| Logs | 發生了哪個事件？例外內容是什麼？ | Loki |
| Traces | 這次 Request 慢在哪裡、斷在哪裡？ | Tempo |

建立 Evidence 目錄：

```bash
mkdir -p evidence/day03
```

建議每個實驗至少留下：

```text
evidence/day03/
├── baseline.csv
├── latency.csv
├── timeout.txt
├── http-500.txt
├── database-down.txt
├── container-crash.txt
└── observations.md
```

本文會告訴你預期看見什麼。

請把自己真正觀察到的數值寫進 `observations.md`。

沒有執行過的數值，不能突然長成「實驗結果」。

---

# ⑤ 實驗前先加入 PostgreSQL Probe

Day 2 雖然啟動了 PostgreSQL，但 Application 還沒有使用它。

如果現在直接停止 PostgreSQL：

```text
PostgreSQL down
FastAPI 完全沒感覺
User 完全沒感覺
```

這只代表我們很會停止 container。

所以今天加入一條真的會碰 PostgreSQL 的 endpoint。

## 安裝 Psycopg 3

```bash
uv add "psycopg[binary]"
uv sync
```

官方套件名稱是：

```text
psycopg
```

不是：

```text
psycopg3
```

`[binary]` 適合本機 Lab，因為它帶有需要的 binary dependencies。Production 是否採用 binary、local build 或系統 `libpq`，應依映像建置與安全更新策略決定。

## 加入環境變數

在 `api` service 加入：

```yaml
services:
  api:
    environment:
      DATABASE_URL: postgresql://sre:sre@postgres:5432/sre_lab
      CHAOS_ENABLED: "true"
```

PostgreSQL service 使用相同資料：

```yaml
services:
  postgres:
    image: postgres:18
    environment:
      POSTGRES_USER: sre
      POSTGRES_PASSWORD: sre
      POSTGRES_DB: sre_lab
```

這組帳密只用在本機 Lab。

## 加入 Database Endpoint

在 `app/main.py` 增加：

```python
import logging
import os

import psycopg
from fastapi import HTTPException
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


logger = logging.getLogger("sre_lab")
tracer = trace.get_tracer(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sre:sre@postgres:5432/sre_lab",
)


@app.get("/api/database")
async def database_demo() -> dict[str, str | int]:
    with tracer.start_as_current_span("postgres.select_one") as span:
        try:
            connection = await psycopg.AsyncConnection.connect(
                DATABASE_URL,
                connect_timeout=1,
            )

            async with connection:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    row = await cursor.fetchone()

            return {
                "status": "ok",
                "result": row[0],
            }

        except psycopg.Error as exc:
            span.set_status(
                Status(
                    StatusCode.ERROR,
                    "postgres unavailable",
                )
            )
            span.set_attribute(
                "error.type",
                type(exc).__qualname__,
            )

            logger.exception(
                "database request failed",
                extra={
                    "dependency": "postgres",
                },
            )

            raise HTTPException(
                status_code=503,
                detail="Database unavailable",
            ) from exc
```

這裡刻意設定：

```text
connect_timeout = 1 second
```

因為 dependency 出問題時，沒有 timeout 的等待會持續占用 Application 資源。

Timeout 不會治好 PostgreSQL。

它只是替傷害設定上限。

OpenTelemetry 在 2026 年的文件中，已將事件與例外的處理方向移向 Logs API。本篇不手動呼叫 `span.record_exception()`，改用 structured log 保存 exception，再以 span status 與 `error.type` 標記 trace。這樣可以避免在新程式碼中繼續依賴正在淡出的 Span Event API。

參考：[OpenTelemetry：Deprecating Span Events API](https://opentelemetry.io/blog/2026/deprecating-span-events/)

重新建置：

```bash
docker compose up -d --build api postgres
```

確認正常：

```bash
curl -i http://localhost:8000/api/database
```

預期：

```http
HTTP/1.1 200 OK
```

```json
{
  "status": "ok",
  "result": 1
}
```

---

# ⑥ 建立 Baseline：先知道正常長什麼樣

沒有 baseline，就很容易出現這種 Incident Update：

> P95 變成 800 ms，好像很慢。

問題是：

> 平常是多少？

> 不知道。

非常有偵探感。

先確認所有 services：

```bash
docker compose ps
```

再確認四個入口：

```bash
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
curl -i http://localhost:8000/api/demo
curl -i http://localhost:8000/api/database
```

全部應先成功。

接著建立 60 次正常 Request：

```bash
for i in {1..60}; do
  curl \
    --silent \
    --show-error \
    --output /dev/null \
    --write-out "%{http_code},%{time_total}\n" \
    http://localhost:8000/api/demo

  sleep 0.2
done | tee evidence/day03/baseline.csv
```

檔案內容會像：

```csv
200,0.012341
200,0.010928
200,0.011507
```

這裡的數字只是格式示例，不是你的實驗結果。

## Prometheus Baseline

Request rate：

```promql
sum(
  rate(
    http_requests_total{
      route="/api/demo"
    }[1m]
  )
)
```

5xx ratio：

```promql
sum(
  rate(
    http_requests_total{
      route="/api/demo",
      status_code=~"5.."
    }[1m]
  )
)
/
clamp_min(
  sum(
    rate(
      http_requests_total{
        route="/api/demo"
      }[1m]
    )
  ),
  0.000001
)
```

P95 latency：

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(
      http_request_duration_seconds_bucket{
        route="/api/demo"
      }[1m]
    )
  )
)
```

Prometheus 的 `histogram_quantile()` 是依 bucket 估算 quantile。

所以結果精度會受 bucket 邊界影響。

它不是把每一次 Request 精確排序後取第 95 個百分位。

參考：[Prometheus query functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)

## Baseline 記錄

在 `observations.md` 寫下：

```markdown
## Baseline

- Time window:
- Request count:
- HTTP success rate:
- P50:
- P95:
- P99:
- Prometheus target:
- Unexpected logs:
```

先記錄，再破壞。

---

# ⑦ 實驗一：服務沒有錯，只是慢到像壞掉

Day 2 已經替 `/api/demo` 留下 `delay_ms`。

先直接送一次三秒 Request：

```bash
curl \
  --silent \
  --output /dev/null \
  --write-out "status=%{http_code} total=%{time_total}s\n" \
  "http://localhost:8000/api/demo?delay_ms=3000"
```

你應該看到：

```text
status=200
total≈3 seconds
```

HTTP 成功。

使用者等待三秒。

兩件事可以同時成立。

## 製造 5% 的 Slow Requests

```bash
for i in {1..100}; do
  if (( i % 20 == 0 )); then
    delay_ms=3000
  else
    delay_ms=0
  fi

  curl \
    --silent \
    --show-error \
    --output /dev/null \
    --write-out "%{http_code},%{time_total}\n" \
    "http://localhost:8000/api/demo?delay_ms=${delay_ms}"
done | tee evidence/day03/latency.csv
```

這組流量是：

```text
95 normal requests
5 slow requests
```

## 預期 Evidence

| 視角 | 預期現象 |
| --- | --- |
| User | 少數 Request 明顯變慢，但仍拿到 200 |
| Metrics | Error ratio 維持接近 0；P95/P99 可能上升 |
| Logs | `status_code=200`，但 `duration_ms` 接近 3000 |
| Traces | `/api/demo` span duration 接近 3 秒 |

注意「可能上升」。

實際 P95 會受樣本數、scrape window、bucket 設計與邊界插值影響。

如果 P95 沒有明顯變化，查看 P99，或提高 slow request 比例。

不要為了符合文章預期，硬說 Dashboard 有變。

## 這個實驗看到了什麼？

```text
HTTP 200
   ≠
Good User Experience
```

Error Rate 看不到「成功但很痛苦」的 Request。

這也是後面為什麼要同時建立：

```text
Availability SLI
Latency SLI
```

---

# ⑧ 實驗二：Client Timeout 與 Server Success 可以同時發生

現在讓 server 等三秒，但 client 只願意等一秒：

```bash
curl \
  --max-time 1 \
  --silent \
  --show-error \
  --output /dev/null \
  --write-out "status=%{http_code} total=%{time_total}s\n" \
  "http://localhost:8000/api/demo?delay_ms=3000" \
  2>&1 | tee evidence/day03/timeout.txt
```

`curl --max-time` 會限制整個 transfer 可使用的時間。

常見結果：

```text
curl: (28) Operation timed out
status=000
```

但是 server 端可能仍然繼續處理 coroutine；如果工作最後完成，server metric 或 log 可能仍會記成一次 `200`。

因此你可能得到：

| 觀察位置 | 結果 |
| --- | --- |
| Client | Timeout，任務失敗 |
| Server metric | Request 最後可能被記成 200 |
| Server log | 可能仍出現 completed |
| Trace | 可能仍顯示 server span 完成 |

實際結果要看 ASGI server 的 disconnect handling，以及程式是否取消工作。

Zalando 的 timeout 指南也提醒：client 關閉連線後，如果 server 沒有適當的 timeout 或 cancellation，request 仍可能繼續處理，持續占用 thread、HTTP connection 與 database connection。

這不是我們自己實驗室才有的巧合。[ClickHouse GitHub Issue #65117](https://github.com/ClickHouse/ClickHouse/issues/65117) 記錄了幾乎一樣的情境：client 端因 receive timeout 中斷連線，server 端卻仍完整處理完 request、回傳 `HTTP 200`。不同的 stack，同一種「client 認為失敗、server 認為成功」的落差。

Client 已經放棄，不代表 server 的工作自動消失。

> **只從 server 端計算成功率，可能高估使用者真正拿到回應的比例。**

Production 通常還需要：

```text
Load balancer metrics
API gateway metrics
Client telemetry
Synthetic monitoring
```

參考：[curl man page](https://curl.se/docs/manpage.html)、[Zalando：All You Need to Know About Timeouts](https://engineering.zalando.com/posts/2023/07/all-you-need-to-know-about-timeouts.html)

---

# ⑨ 實驗三：製造真正的 Application Exception

Day 2 使用 `HTTPException(status_code=500)`。

它可以測 5xx counter，卻不等於未預期的程式例外。

如果我們想觀察 stack trace 與 error span，就要真的丟出 exception。

把 `/api/demo` 的 failure 部分改成：

```python
import logging

from fastapi import Query
from typing import Annotated


logger = logging.getLogger("sre_lab")


@app.get("/api/demo")
async def demo(
    delay_ms: Annotated[
        int,
        Query(ge=0, le=10_000),
    ] = 0,
    fail: bool = False,
) -> dict[str, str]:
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    if fail:
        try:
            raise RuntimeError(
                "Injected application failure"
            )
        except RuntimeError:
            logger.exception(
                "injected application failure"
            )
            raise

    return {
        "message": "SRE Lab is running",
        "timestamp": datetime.now(UTC).isoformat(),
    }
```

這裡順手替 `delay_ms` 加上最大值，避免有人不小心送出：

```text
delay_ms=999999999
```

然後等待到下一屆鐵人賽。

重新建置並送出 Request：

```bash
docker compose up -d --build api

curl \
  --include \
  "http://localhost:8000/api/demo?fail=true" \
  2>&1 | tee evidence/day03/http-500.txt
```

## 預期 Evidence

### User

```http
HTTP/1.1 500 Internal Server Error
```

### Prometheus

```promql
sum(
  increase(
    http_requests_total{
      route="/api/demo",
      status_code="500"
    }[5m]
  )
)
```

### Loki

如果 Day 2 已經替 Alloy 加上 `service="api"` label：

```logql
{service="api"} |= "Injected application failure"
```

如果尚未完成 label relabeling，先用 Compose container label 或直接在 Explore 選取實際 label。

Alloy 的 `loki.source.docker` 仍是現行元件，會讀取 Docker container logs 並轉送給 Loki pipeline。

參考：[Grafana Alloy：loki.source.docker](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.docker/)

### Tempo

找到 `/api/demo` trace，檢查：

```text
HTTP status = 500
Span status = ERROR
Exception / error attributes
Duration
```

OpenTelemetry 的 FastAPI instrumentation 會替 HTTP request 建立 server span。實際 exception 欄位會受 instrumentation 與 semantic convention 版本影響，所以不要把查詢綁死在單一舊欄位名稱。

## 三種訊號各自回答什麼？

```text
Metrics
「500 正在增加嗎？」

Logs
「RuntimeError 的內容與 stack trace 是什麼？」

Trace
「哪一次 Request、哪個 span 失敗？」
```

同一份資料重複存三次沒有意義。

三種訊號應該各自降低不同的未知數。

---

Netflix 後來用 [FIT](https://netflixtechblog.com/fit-failure-injection-testing-35d8e2a9bb2) 把 dependency failure 變成可控的 request-level 實驗：先限制在測試帳號或裝置，再逐步擴大到少量 production traffic。它可以注入 latency 或 persistence-layer failure，檢查上游的 timeout、fallback 與隔離機制。

接下來停止 PostgreSQL，就是這個思路的本機版本。

# ⑩ 實驗四：PostgreSQL 掛了，但 FastAPI 還活著

先確認資料庫路徑正常：

```bash
curl -i http://localhost:8000/api/database
```

接著停止 PostgreSQL：

```bash
docker compose stop postgres
```

再測三條路徑：

```bash
{
  curl -i http://localhost:8000/health
  curl -i http://localhost:8000/ready
  curl -i http://localhost:8000/api/database
} 2>&1 | tee evidence/day03/database-down.txt
```

依 Day 2 的實作，預期結果是：

| Endpoint | 預期結果 | 原因 |
| --- | --- | --- |
| `/health` | 200 | FastAPI process 還活著 |
| `/ready` | 200 | Day 2 的 readiness 目前仍是固定回傳 |
| `/api/database` | 503 | Critical dependency 無法連線 |

這裡的 `/ready = 200` 不是最佳實作，因為它沒有檢查 PostgreSQL。

它是 Day 2 故意留下的簡化版本。

今天的實驗會看到：

> **Health endpoint 存在，不代表它真的描述了使用者的 Critical Path。**

## 預期 Evidence

| 視角 | 預期現象 |
| --- | --- |
| User | DB endpoint 快速收到 503，而非無上限等待 |
| Metrics | `/api/database` 的 503 增加；FastAPI target 仍為 UP |
| Logs | `database request failed` 與 PostgreSQL connection error |
| Traces | `postgres.select_one` 為 ERROR；HTTP request 為 503 |

這個實驗也會看到：

```text
Application UP
     ≠
Every Feature Available
```

Cloudflare 在 2023 年那次控制平面與 Analytics 服務中斷（[Post mortem on the Cloudflare Control Plane and Analytics Outage](https://blog.cloudflare.com/post-mortem-on-cloudflare-control-plane-and-analytics-outage/)）是同一種問題的規模放大版：Kafka 與 ClickHouse 只跑在 PDX-04 一個機房，理論上依賴它們的服務應該由 high-availability cluster 接手，但這些依賴其實藏在沒被驗證過的角落。Cloudflare 官方事後坦承：「we had never tested fully taking the entire PDX-04 facility offline」——沒被 fail over 測試驗證過的 dependency，跟不存在的 fallback 沒有兩樣。今天我們主動停掉 PostgreSQL，就是在自己的 Lab 裡先把這種未知數找出來，而不是等 production 幫你找。

## 恢復 PostgreSQL

```bash
docker compose start postgres
```

等待 healthcheck 通過後：

```bash
docker compose ps postgres
curl -i http://localhost:8000/api/database
```

一定要驗證 Recovery。

停止故障注入，不代表服務已恢復。

---

# ⑪ 實驗五：直接殺掉 API Container

Application exception 發生在 process 裡。

現在把 process 本身移除。

先開一個 Terminal 持續探測：

```bash
while true; do
  date -u +"%Y-%m-%dT%H:%M:%SZ"

  curl \
    --max-time 1 \
    --silent \
    --show-error \
    --output /dev/null \
    --write-out "status=%{http_code} total=%{time_total}s\n" \
    http://localhost:8000/health

  sleep 1
done
```

在另一個 Terminal 執行：

```bash
docker compose kill -s SIGKILL api
```

`SIGKILL` 不允許 process 執行 graceful shutdown。

這和正常的：

```bash
docker compose stop api
```

不是同一種故障。

`stop` 會先送出 termination signal 並等待 grace period；`kill -s SIGKILL` 會直接終止 process。

查看狀態：

```bash
docker compose ps -a api

container_id="$(docker compose ps -a -q api)"

docker inspect \
  --format 'exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  "${container_id}" \
  | tee evidence/day03/container-crash.txt
```

常見 exit code 是：

```text
137
```

它通常表示 process 被 `SIGKILL` 終止。

## 預期 Evidence

| 視角 | 預期現象 |
| --- | --- |
| User | 直接連 port 8000 時常見 connection refused 或 connection reset |
| Metrics | `up{job="sre-lab-api"}` 變成 0；container 死亡期間 application counters 停在最後值，但 process 重啟後會歸零 |
| Logs | API 不再產生新 application log；可能看見中斷前最後訊息 |
| Traces | 不再產生新的 application trace；進行中的 trace 可能不完整 |

查 Prometheus：

```promql
up{
  job="sre-lab-api"
}
```

Prometheus 的 `up` metric 是 scrape 層的證據：

```text
1 = scrape succeeded
0 = scrape failed
```

參考：[Prometheus：Jobs and instances](https://prometheus.io/docs/concepts/jobs_instances/)

## 為什麼看不到 502？

因為目前架構是：

```text
Client → FastAPI:8000
```

中間沒有 reverse proxy 或 load balancer。

502 通常是前一層 proxy 想連 upstream，卻拿不到有效回應時產生。

這個 Lab 直接連 API，所以 connection refused 才是合理結果。

## 恢復 API

```bash
docker compose up -d api
curl -i http://localhost:8000/health
```

如果 Compose 設有 restart policy，結果會依 policy 與終止方式而不同。不要假設 container 一定自動回來；用實際狀態判斷。

參考：[Docker Compose service restart](https://docs.docker.com/reference/compose-file/services/#restart)

還有一件事容易讓人誤會：`prometheus-client` 的 Counter 是 process 記憶體內的狀態，不是外部持久化的值。API process 被 `SIGKILL` 或 OOM 殺掉、重新啟動後，先前累積的 `http_requests_total` 會直接歸零，不會延續舊的計數。這不是本專案獨有的行為，[Prometheus 官方 client library 文件](https://prometheus.io/docs/instrumenting/writing_clientlibs/) 就明確規定 Counter 在 process 重啟後歸零是預期規範，而不是某個 library 沒做好。

如果你想保留某次故障（例如前面 HTTP 500 實驗）的計數證據，要在還沒重啟 process 前先查詢並記錄下來，不要留到全部實驗做完才回頭查 Prometheus。

---

# ⑫ 可選實驗：Memory Exhaustion

這個實驗會真的讓 API process 被 OOM kill。

只在本機隔離 Lab 執行。

先限制 API container：

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 256M
    environment:
      CHAOS_ENABLED: "true"
```

本文採用現行 Compose Specification 的 `deploy.resources.limits.memory`。

> **Note：** 舊版 Compose 文件與既有範例常見 service-level `mem_limit: 256m`。現行 Compose Specification 仍保留這個 key，並非已失效；若與 `deploy.resources.limits.memory` 同時使用，兩者必須一致。本文統一採用後者。

實際限制仍由本機 container runtime 實作。執行前先用下列指令確認 Compose 接受設定：

```bash
docker compose config
```

在 `app/main.py` 增加：

```python
import asyncio
import os

from fastapi import HTTPException, Query
from typing import Annotated


def require_chaos_enabled() -> None:
    if os.getenv("CHAOS_ENABLED") != "true":
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )


@app.get("/api/consume-memory")
async def consume_memory(
    megabytes: Annotated[
        int,
        Query(ge=1, le=512),
    ] = 300,
) -> dict[str, int]:
    require_chaos_enabled()

    chunks: list[bytearray] = []

    for _ in range(megabytes):
        chunk = bytearray(1024 * 1024)

        # Touch each memory page so the allocation becomes resident.
        chunk[::4096] = b"x" * len(chunk[::4096])

        chunks.append(chunk)
        await asyncio.sleep(0)

    await asyncio.sleep(30)

    return {
        "allocated_megabytes": len(chunks),
    }
```

重新建置：

```bash
docker compose up -d --build api
```

開一個 Terminal 觀察：

```bash
docker stats
```

另一個 Terminal 執行：

```bash
curl -i \
  "http://localhost:8000/api/consume-memory?megabytes=300"
```

由於 Python process 本身已占用部分記憶體，實際 OOM 發生點不會剛好是 256 MB。

確認：

```bash
container_id="$(docker compose ps -a -q api)"

docker inspect \
  --format 'exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  "${container_id}"
```

如果 runtime 正確套用限制，預期可看見：

```text
oom=true
```

## 這個實驗最重要的觀察

OOM 發生後：

```text
Application 自己的 log
Application 自己的 trace
```

可能來不及 flush。

所以：

> **不能要求一個已經被殺掉的 process，完整解釋自己為什麼死掉。**

你還需要 container runtime、host 或 orchestrator 的證據。

完成後恢復：

```bash
docker compose up -d api
curl -i http://localhost:8000/health
```

參考：[Docker：Resource constraints](https://docs.docker.com/engine/containers/resource_constraints/)

---

# ⑬ 故障與訊號總表

| 故障 | 使用者 | Metrics | Logs | Traces |
| --- | --- | --- | --- | --- |
| Slow request | 200，但等待變長 | P95/P99 可能上升 | completed + 高 duration | span duration 變長 |
| Client timeout | Client 放棄 | Server 可能仍記 200 | Server 可能仍完成 | Server span 可能仍成功 |
| Application exception | HTTP 500 | 5xx ratio 上升 | stack trace | error span |
| PostgreSQL down | DB 功能回 503 | 503 與 latency 上升，API target 仍 UP | connection error | DB child span error |
| API SIGKILL | 無法連線 | Prometheus `up=0` | 新 app logs 消失 | 新 traces 消失 |
| Memory exhaustion | 中斷、重啟或無法連線 | `up=0`；需額外 runtime metrics 看 memory | app log 可能來不及寫 | trace 可能中斷 |

看這張表時，別只找有資料的格子，也要留意哪裡**沒有資料**。

```text
No application logs
No application traces
```

本身也可能是訊號。

只是你必須搭配外部視角，才能分辨：

```text
真的沒有事件
        vs
Application 已經死到無法回報
```

---

# ⑭ `/health = 200` 到底代表什麼？

今天至少看見三種狀態：

```text
Case A
FastAPI alive
PostgreSQL alive
User request succeeds
```

```text
Case B
FastAPI alive
PostgreSQL down
/health = 200
DB request = 503
```

```text
Case C
FastAPI process gone
/health unreachable
```

所以 `/health = 200` 只表示：

> 這個 endpoint 在這一刻能回應。

它無法保證：

```text
Every dependency is healthy
Every feature works
Every user request succeeds
Latency is acceptable
Response is correct
```

Health check 是一個設計決策。

不是一條加上去就獲得可靠性的魔法 route。

Google SRE Book 還描述了更反直覺的情況：task 因過載而 health check 失敗，排程器重啟它；新 task 啟動後又立刻過載，最後形成反覆重啟的迴圈。

書中的結論很直接：

> “health-checking itself makes the service unhealthy.”

Process health、dependency health 與使用者 Critical Path 必須分開思考。非關鍵 dependency 就算只是卡住不回應，也可能耗盡前端資源，讓原本正常的 request 一起被拒絕。

參考：[Google SRE Book — Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)

---

# ⑮ AI Era Extension：把今天的故障換成 AI Workflow

今天的傳統故障，在 AI Application 裡都有對應版本。

| 今天的 Lab | AI 系統對應 | 使用者影響 |
| --- | --- | --- |
| Slow request | LLM provider 變慢、queue delay、長 context | TTFT 或總回應時間上升 |
| Client timeout | Streaming 中斷、前端先放棄 | Provider 或 server 端可能仍繼續生成；是否計費取決於 API 行為 |
| Application exception | Output parser 或 tool schema failure | Model 已回答，但 API 無法交付 |
| PostgreSQL down | Vector DB、embedding service unavailable | RAG 無法取得 context |
| Container crash | Model server / agent worker crash | Request 中斷 |
| Memory exhaustion | GPU OOM、VRAM exhaustion | Inference worker 被終止 |

這不是假設情境。[vLLM GitHub Issue #30637](https://github.com/vllm-project/vllm/issues/30637) 記錄了 DeepSeek-V3.2 在 sampler warmup 階段觸發 CUDA OOM 導致 inference worker 被終止的真實案例——GPU 記憶體耗盡跟 Day 3 的 host memory exhaustion 是同一種 resource exhaustion，只是換了一層硬體。

傳統 telemetry 可能全部正常：

```text
HTTP 200
Metrics normal
No exception
```

但 LLM 回答仍然可能完全錯誤。Metrics、Logs、Traces 可以告訴我們：

```text
系統怎麼執行
哪裡變慢
哪裡失敗
```

卻不能單獨保證：

```text
答案正確
引用可信
任務完成
輸出安全
```

這就是 Day 1 提過的：

```text
Technical Success
        ≠
Workflow Success
        ≠
Task Success
```

後續我們會再加入 Evaluation。

因為 AI Reliability 的故障，有一部分根本不會長成 500。

Netflix 從 FIT 發展到 [ChAP](https://netflixtechblog.com/chap-chaos-automation-platform-53e6d528371f) 時，把重點放在實驗安全。它用少量 production traffic 建立 control 與 experiment 群組，注入 failure scenario，再用 error-budget circuit breaker 控制 blast radius。ChAP 也整合 Spinnaker 重跑實驗，捕捉 resilience regression。

AI Workflow 的 dependency 更多，實驗順序反而更該保守：

```text
Small traffic
      ↓
Control vs. Experiment
      ↓
Failure injection
      ↓
Abort when impact exceeds budget
```

---

# ⑯ 今天的實驗報告怎麼寫？

在 `evidence/day03/observations.md` 使用這份模板：

```markdown
# Day 03 Failure Injection Report

## Environment

- Date:
- Git commit:
- Docker version:
- Docker Compose version:
- Python version:
- Image tags or digests:

## Baseline

- Request count:
- Success ratio:
- P50:
- P95:
- P99:

## Experiment

- Failure injected:
- Start time:
- End time:
- Expected user impact:
- Actual user impact:

## Evidence

- PromQL:
- Loki query:
- Trace ID:
- Relevant logs:
- Container state:

## Recovery

- Recovery action:
- Recovery time:
- Verification request:
- Remaining anomaly:

## What surprised me

-
```

這份報告保留了故障前後的變化、使用者影響、Evidence 與 Recovery 驗證，不只是記錄「Grafana 圖變紅」。

因為它保留：

```text
What changed
When it changed
How users were affected
What evidence existed
How recovery was verified
```

之後做 Incident Timeline 與 Postmortem 時，會直接用到同一種思考方式。

---

# ⑰ 驗收清單

```text
[ ] 所有 services 在實驗前正常
[ ] 已留下 baseline request data
[ ] 已觀察 slow request 的 latency 變化
[ ] 已區分 client timeout 與 server-side status
[ ] 已製造一次真正的 RuntimeError
[ ] 已在 Prometheus 找到 500
[ ] 已在 Loki 找到 exception log
[ ] 已在 Tempo 找到 error trace
[ ] 已停止 PostgreSQL
[ ] 已確認 /health 與 DB endpoint 呈現不同狀態
[ ] 已用 SIGKILL 終止 API container
[ ] 已觀察 Prometheus up 變成 0
[ ] 已完成至少一次 recovery verification
[ ] 已記錄實測值，而非複製預期值
```

Memory exhaustion 是可選實驗。

前四類故障與 recovery 全部完成，就已經達成 Day 3 的主要目標。

---

# ⑱ Production Takeaway

今天的實驗留下五個判斷：

* container 顯示 Running，只代表 process 還在。
* HTTP 200 只代表 Request 完成，不代表它夠快。
* Application 活著，不代表 dependency 或 Critical Path 正常。
* process 死掉後，application logs 與 traces 也可能一起消失。
* Recovery 必須重新驗證，不能只看你已經執行 `start` 或 `up`。

這也是為什麼 Reliability 不能只靠一個工具：

```text
Metrics detect the pattern.
Logs explain the event.
Traces locate the path.
User signals define the impact.
```

裝好 Grafana 還不算完成 Observability。系統偏離預期時，你得回答：

```text
誰受到影響？
影響多大？
從什麼時候開始？
故障在哪一層？
我們真的恢復了嗎？
```

如果回答不了，Dashboard 再漂亮也只是一張很貴的桌布。

---

# 下一篇：Day 04｜什麼是 SRE？

我們已經建立服務，也親手把它弄壞。

下一篇終於回到最基本的問題：

> Site Reliability Engineering 到底是什麼？

我們會從今天看到的故障出發，理解：

```text
Software Engineering
        ×
Operations
        ×
Reliability Decisions
```

以及為什麼 SRE 的目標從來不是：

```text
Zero Failure
```

而是用工程方法，在使用者期待、系統風險與交付速度之間管理 Reliability。

---

> 這篇是 **Learning SRE for the AI Era** 系列的一部分。
>
> 我會從 SRE 的服務可靠性基礎開始，逐步探索當系統加入 LLM、RAG、Agent 與 GPU Infrastructure 後，如何讓 AI 系統不只可用，也能被觀測、評估、控制成本並安全演進。
>
> **Build → Trace → Break → Measure → Evaluate → Recover → Improve.**
