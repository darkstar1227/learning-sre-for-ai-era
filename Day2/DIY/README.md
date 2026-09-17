# Day2 DIY — SRE Lab：FastAPI + Docker Compose + Observability Stack

對應 [Day2/Day2.md](../Day2.md) 的實作驗證。獨立 `uv` 專案，與 Day0/Day1 完全分開；本篇額外用 Docker Compose 起 9 個 container。

## 內容

```text
Day2/DIY/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI: /health /ready /api/demo /metrics + middlewares
│   ├── metrics.py        # Prometheus Counter/Histogram/Gauge
│   ├── logging.py        # JSON structured logging (stdout)
│   └── telemetry.py      # OpenTelemetry → OTLP/gRPC → otel-collector
├── observability/
│   ├── prometheus/prometheus.yml
│   ├── grafana/provisioning/datasources/datasources.yml
│   ├── loki/loki-config.yml
│   ├── alloy/config.alloy
│   ├── tempo/tempo.yml
│   └── otel/collector-config.yml
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── uv.lock
```

## 執行方式

```bash
cd Day2/DIY
make up      # docker compose up -d --build
make ps
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/api/demo
curl "http://localhost:8000/api/demo?delay_ms=500"
curl "http://localhost:8000/api/demo?fail=true"
make down    # 或 make reset 連 volume 一起清
```

Grafana: http://localhost:3000 (admin/admin)
Prometheus: http://localhost:9090

## 實測結果（實際跑過 `docker compose up -d --build`）

全部 9 個 service（api / postgres / redis / prometheus / grafana / loki / alloy / otel-collector / tempo）都成功 `Up`，逐項對照文章 Day 2 的最低驗收標準：

- [x] `docker compose up -d --build` 成功
- [x] `/health` → `200 {"status":"ok"}`
- [x] `/ready` → `200 {"status":"ready"}`
- [x] `/api/demo` 正常回傳
- [x] `/api/demo?delay_ms=300` 確實延遲（Tempo 上量到 `durationMs: 301`）
- [x] `/api/demo?fail=true` → `500`
- [x] Prometheus 成功 scrape `/metrics/`（`targets` API 回傳 `health: up`）
- [x] `http_requests_total` 有資料（含 200/500 各 label）
- [x] `http_request_duration_seconds_count` 有資料
- [x] FastAPI 輸出 JSON structured logs（stdout 可看到含 `request_id`/`duration_ms` 的 JSON）
- [x] Alloy 能收集 Docker logs（Loki 查得到 API container 的原始 log line）
- [~] Loki 可以查到 API log — **能查到，但不是用文章寫的 `{service="api"}`**（見下方問題 1）
- [x] 每個 Request 都有 Request ID（log 裡的 `request_id` 欄位）
- [x] FastAPI trace 能送到 OTel Collector 再到 Tempo（`tempo:3200/api/search` 查得到 `GET /api/demo` / `GET /metrics` traces，含正確 duration）
- [x] Grafana 可以查 Prometheus / Loki / Tempo（`/api/datasources` 確認三個 datasource 都 provisioning 成功）
- [x] 環境可以停止並重新建立（`docker compose down` 正常關閉）

## 發現的問題

1. **文章裡查 Loki 的範例 `{service="api"}` 在預設 Alloy 設定下查不到任何東西。**
   文章 `config.alloy` 只用了最基本的 `discovery.docker` + `loki.source.docker`，沒有加 `relabel_configs`。實測結果是 Alloy 把所有 container 的 log 都送進 Loki，但唯一的 label 是 `service_name="unknown_service"`，並沒有依照 container name（例如 `api`）自動產生 `service` 這個 label。也就是說，文章 Grafana Explore 章節寫的：
   ```logql
   {service="api"}
   ```
   實測會查到 0 筆結果。要讓這條查詢真的可用，`config.alloy` 需要額外加 `discovery.relabel`，把 `__meta_docker_container_name` 轉成 `service` 這個 label，文章目前沒有提到這一步，跟著操作會卡在「Loki 有資料但 LogQL 查不到」。
   同一個根因還有一個延伸現象：`discovery.docker` 預設收的是整台 Docker host 上*所有*container 的 log，不只是這個 Compose 專案裡的 9 個服務。本機如果同時跑著其他 container（例如某個 tunnel/agent），它們的 log 一樣會被送進同一個 Loki、疊在同一個 `service_name="unknown_service"` label 下。加上 `discovery.relabel` 用 container name 分流，順便也能把非本專案的 container 過濾掉，避免不同專案的 log 混在一起查。
2. **Postgres/Redis 目前完全沒有 healthcheck，`depends_on` 只保證啟動順序，不保證真的 ready。** 這符合文章「先跑起來、不寫 CRUD」的定位，沒有錯，但如果照抄這份 `docker-compose.yml` 直接接上真正的 DB 存取，會遇到 `api` container 比 Postgres 早準備好而連線失敗的競態問題。文章對這點沒有著墨，先記錄下來留給 Day 3 之後處理 Dependency Failure 時參考。
3. **本地（非 docker）直接 `uv run uvicorn` 啟動時，OTel exporter 會持續印出 `Transient error ... errors resolving otel-collector:4317: Domain name not found`。** 這是預期行為（`otel-collector` 這個 hostname 只在 Docker Compose network 裡能解析），不是 bug，但文章沒有特別提醒「這份程式碼設計上只能在 Compose 環境裡完整運作」，本機單獨跑 `app/main.py` 做開發時務必留意這條噪音 log。
4. 其餘部分（Prometheus scrape config、Metrics middleware、`/api/demo` 故障注入、OTel Collector → Tempo pipeline、Grafana datasource provisioning）皆與文章描述一致，`docker-compose.yml` 用文章給的 image 清單（`prom/prometheus`、`grafana/grafana`、`grafana/loki`、`grafana/alloy`、`otel/opentelemetry-collector-contrib`、`grafana/tempo`）都能正常啟動，不需要額外調整版本即可跑通全部驗收項目。
