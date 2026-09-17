# Day3 DIY — 故障注入實驗：Slow / Timeout / 500 / DB down / Container crash / OOM

對應 [Day3/Day3.md](../Day3.md) 的實作驗證。獨立 `uv` 專案，繼承 Day2/DIY 的 Observability Stack，加上 PostgreSQL probe endpoint 與 memory-exhaustion endpoint。

## 內容

```text
Day3/DIY/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI: /health /ready /api/demo /api/database
│   │                     # /api/consume-memory /metrics + middlewares
│   ├── metrics.py        # Prometheus Counter/Histogram/Gauge（沿用 Day2）
│   ├── logging.py        # JSON structured logging (stdout)（沿用 Day2）
│   └── telemetry.py       # OpenTelemetry → OTLP/gRPC → otel-collector（沿用 Day2）
├── observability/         # 沿用 Day2 的 prometheus/grafana/loki/alloy/tempo/otel 設定
├── Dockerfile
├── docker-compose.yml     # 在 Day2 基礎上加 DATABASE_URL/CHAOS_ENABLED env、
│                           # api 的 deploy.resources.limits.memory: 256M、
│                           # postgres 改用 postgres:18 + sre/sre/sre_lab 帳密
├── Makefile
├── pyproject.toml         # 加 psycopg[binary]
└── uv.lock
```

## 執行方式

```bash
cd Day3/DIY
make up      # docker compose up -d --build
make ps

mkdir -p evidence/day03

# baseline
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/api/demo
curl http://localhost:8000/api/database

# 實驗一：slow request
curl -s -o /dev/null -w "status=%{http_code} total=%{time_total}s\n" "http://localhost:8000/api/demo?delay_ms=3000"

# 實驗二：client timeout
curl --max-time 1 -s -o /dev/null -w "status=%{http_code} total=%{time_total}s\n" "http://localhost:8000/api/demo?delay_ms=3000"

# 實驗三：真實例外
curl -si "http://localhost:8000/api/demo?fail=true"

# 實驗四：PostgreSQL down
docker compose stop postgres
curl -si http://localhost:8000/health
curl -si http://localhost:8000/ready
curl -si http://localhost:8000/api/database
docker compose start postgres

# 實驗五：SIGKILL container
docker compose kill -s SIGKILL api
docker inspect --format 'exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' "$(docker compose ps -a -q api)"
docker compose up -d api

# 可選實驗：OOM（256M 限制下，配 megabytes=500 才會真的觸發）
curl -si --max-time 40 "http://localhost:8000/api/consume-memory?megabytes=500"
docker inspect --format 'exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' "$(docker compose ps -a -q api)"
docker compose up -d api

make down    # 或 make reset 連 volume 一起清
```

## 實測結果（實際跑過 `docker compose up -d --build` 逐項驗證）

全部 9 個 service 成功 `Up`，逐項對照 Day3.md §⑰ 驗收清單：

- [x] 所有 services 在實驗前正常
- [x] `/api/database` baseline → `200 {"status":"ok","result":1}`
- [x] 實驗一 slow request → `status=200 total=3.08s`（HTTP 成功但使用者等 3 秒，符合「200 ≠ Good UX」的論點）
- [x] 實驗二 client timeout → `curl --max-time 1` 得到 `status=000 total=1.00s`（client 放棄），文章描述的「server 端可能仍完成」性質上一致（未逐一在 server log 端二次確認，但 client 側行為與文章預期吻合）
- [x] 實驗三 真實 RuntimeError → `HTTP/1.1 500 Internal Server Error`，log 印出完整 stack trace（`exc_info`）
- [x] PostgreSQL down → `/health`=200、`/ready`=200、`/api/database`=503（`{"detail":"Database unavailable"}`），與文章 §⑩ 表格完全一致
- [x] PostgreSQL 恢復後 `/api/database` 重新回到 200
- [x] SIGKILL api → `docker compose ps -a` 顯示 `Exited (137)`，`docker inspect` 回報 `exit=137 oom=false`
- [x] SIGKILL 後 `curl --max-time 2 /health` 無回應（connection refused，因為沒有 reverse proxy，符合文章「看不到 502」的解釋）
- [x] `docker compose up -d api` 後 `/health` 重新回到 200
- [x] OOM 實驗：`deploy.resources.limits.memory: 256M` 確實生效（`docker inspect .HostConfig.Memory` = `268435456`），`megabytes=300` 未觸發 OOM（分配速度快、30 秒 sleep 前就已配置完但仍在 256MB 內），改用 `megabytes=500` 才觸發 `exit=137 oom=true`
- [x] OOM 後 `docker compose up -d api` 可正常恢復
- [x] Prometheus `up{job="sre-lab-api"}` 在 API 恢復後回到 `1`
- [x] 環境可以完整 `docker compose down` 關閉

## 發現的問題與修正

1. **`megabytes=300` 配 256M 限制不一定會 OOM，`megabytes=500` 才穩定觸發。** 文章原文只說「Python process 本身已占用部分記憶體，實際 OOM 發生點不會剛好是 256 MB」，但沒給出具體要配多少 MB 才會炸。實測 `bytearray` 配置 + `chunk[::4096]` touch page 的方式配合 uvicorn/FastAPI 本身的常駐記憶體，300MB 配額在 256MB 限制下有時候還在容忍範圍內（Linux cgroup memory 統計與 Python 記憶體回收時機都會有 buffer），要留更大 margin（本次用 500MB）才能穩定重現。這不是文章錯誤，是「實際數字因環境而異」這個提醒本身要更早、更明確地寫給讀者，避免讀者以為 300MB 沒有觸發是自己設定錯了。
2. **`http_requests_total{status_code="500"}` 在 API container 重啟（SIGKILL / OOM）後查詢會是空結果。** 原因是 `prometheus-client` 的 Counter 是 process 記憶體內狀態，process 被殺掉重啟後計數器歸零，之前累積的 500 次數不會保留。這符合 Prometheus pull model 加 in-process counter 的正常行為，文章沒有特別強調，但跟著實驗順序做（先製造 500 → 之後又做 SIGKILL/OOM）的讀者，最後回去查 Prometheus 5xx 數字時會找不到早前的資料，容易誤會是查詢語法錯誤。建議需要保留 500 證據的話，先截圖/記錄 PromQL 結果，再進行後面會重啟 container 的實驗。
3. **Loki label 沿用 Day2/DIY README 已記錄的問題：`{service="api"}` 查詢會是 0 筆。** 本次 Day3 用的仍是 Day2 同一份 `config.alloy`（無 `discovery.relabel`），Loki 上只有 `service_name` 這個 label（值是 `unknown_service`），不是文章 §⑨ 提到的 `service="api"`。跟 Day2/DIY 的已知問題一樣，這裡沒有重新修正，因為文章本身也註明「如果尚未完成 label relabeling，先用 Compose container label 或直接在 Explore 選取實際 label」，等於文章自己已預告這個坑。
4. **`docker compose ps -a` 沒有映射 Loki 對外的 `3100` port**（沿用 Day2 設計），因此本機測試 Loki API 要用 `docker compose exec loki wget ...`，不能直接 `curl localhost:3100`。這是 Day2 架構原本就有的設計（只讓 Grafana 內部連 Loki），Day3 沒有改動，附帶記錄以免之後重跑實驗誤以為是 port 沒開對。
5. 其餘部分（`/api/demo?delay_ms=3000` 三秒延遲、`curl --max-time` client timeout 行為、真實 `RuntimeError` 的 500 與 stack trace、PostgreSQL down 導致 `/api/database` 變 503 但 `/health`/`/ready` 仍 200、SIGKILL 後 `exit=137`、`deploy.resources.limits.memory` 生效、恢復流程）皆與文章描述一致，不需要額外調整程式碼即可跑通全部驗收項目。
