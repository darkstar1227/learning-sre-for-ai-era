# Day6 DIY — Reliability Definition

對應 [Day6/Day6.md](../Day6.md) 的實作。此目錄繼承 Day3/Day4/Day5/DIY 的 FastAPI、Observability Stack 與 Charter/Responsibility Map；本日不新增 Endpoint 或 Runtime behavior，新增的工程產物是 [Reliability Definition](docs/reliability-definition.md)。

## 內容

```text
Day6/DIY/
├── docs/
│   ├── service-reliability-charter.md        # 繼承 Day4
│   ├── reliability-responsibility-map.md      # 繼承 Day5
│   └── reliability-definition.md              # Day6 新增
├── app/                  # 繼承 Day3/Day4 的 FastAPI 與故障注入 endpoints
├── observability/        # Prometheus、Loki、Tempo、Alloy、OTel 設定
├── docker-compose.yml
└── README.md
```

Reliability Definition 把 Day6 文章拆出的五個維度（Availability、Latency、Correctness、Durability、Recoverability），套在本 Lab 唯一真正跑得起來的使用者任務——呼叫 `/api/demo` 取得回應——上，逐項回答：

- 這個維度的納入範圍、成功／失敗定義是什麼
- 目前有哪些 evidence 能佐證（metric、log、trace、已重跑過的故障注入實驗）
- 哪些項目誠實標成 `UNKNOWN`，而不是假裝已經定義好

## 執行方式

文件本身可以不啟動 Docker 就檢查結構：

```bash
cd Day6/DIY

test -f docs/reliability-definition.md
grep -n "^## User Task" docs/reliability-definition.md
grep -n "^## Availability" docs/reliability-definition.md
grep -n "^## Latency" docs/reliability-definition.md
grep -n "^## Correctness" docs/reliability-definition.md
grep -n "^## Durability" docs/reliability-definition.md
grep -n "^## Recoverability" docs/reliability-definition.md
grep -n "^## Open Questions" docs/reliability-definition.md
```

預期所有命令都成功，後七個命令會輸出相符行號。

若要驗證文件裡引用的 evidence 確實存在，重新跑一次繼承的服務：

```bash
make up
make ps

curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/api/demo
curl http://localhost:8000/api/database

make down
```

## 實測結果

- [x] `docs/reliability-definition.md` 存在，七個章節（User Task / Request Boundary / Availability / Latency / Correctness / Durability / Recoverability / Open Questions）齊全。
- [x] 每個維度都寫了成功/失敗定義或現況，而不是空白模板。
- [x] 未經驗證的項目（P95 目標、備份機制、RTO/RPO）都標成 `UNKNOWN`，沒有假裝已達成。
- [x] `docker compose up -d --build` 成功啟動全部 9 個容器（api、postgres、redis、prometheus、grafana、loki、alloy、otel-collector、tempo）。
- [x] `GET /health` 回傳 `{"status":"ok"}`。
- [x] `GET /ready` 回傳 `{"status":"ready"}`。
- [x] `GET /api/demo` 回傳 `message` 與 `timestamp`，對應文件裡 Correctness 一節定義的 schema。
- [x] `GET /api/database` 回傳 `{"status":"ok","result":1}`，對應文件裡 Correctness 一節「`result` 必須等於 `1`」的定義。
- [x] `docker compose down` 乾淨清除，沒有殘留容器。

## 發現的問題與修正

1. **文章的 Lab 步驟明講「今天不建立新的 DIY 專案」，但那句話指的是文章裡假想的 `sre-for-ai-era` production 專案，不是本 repo 的驗證流程。** 依照本 repo `CLAUDE.md` 的 SOP，每個 Day 仍要有獨立可驗證的 `DIY/` 目錄；這裡採用「繼承 Day5 stack、只新增文件」的做法，兩者並不衝突，但初次閱讀容易誤會成「這天什麼都不用做」。
2. **模板裡的 Request Boundary 在文章原文用的是假想的 `POST /api/ask`，本 Lab 目前沒有這個 endpoint。** 已改填本 Lab 實際存在、且非故障注入的 `/api/demo`，並在文件裡註明 production 版本應改回 `/api/ask`，避免文件內容和可驗證的程式碼脫節。
3. **Durability／Recoverability 兩節照實填寫後，答案幾乎全是 `UNKNOWN`。** 這不是文件寫壞了，而是本 Lab 目前確實沒有任何備份機制，`docker compose down -v` 會直接清空 PostgreSQL 資料；文章強調「先誠實標記，再談復原」，這份文件正好把這個落差攤開來，而不是提早假裝已有備援。

## 證據邊界

`docs/reliability-definition.md` 是文件層級的練習產物，證明「一個使用者任務可以拆成五個維度分別定義成功/失敗、並標出證據狀態」，不代表：

- 本 Lab 已有真實 production 流量能驗證 Availability 或 Latency 目標。
- PostgreSQL 資料已有任何形式的備份或 restore 演練。
- Correctness 一節列出的 schema 檢查已自動化為 contract test。

以上三項在文件中皆已明確標示為待驗證或 `UNKNOWN`。
