# Day4 DIY — Service Reliability Charter

對應 [Day4/Day4.md](../Day4.md) 的實作。此目錄繼承 Day3/DIY 的 FastAPI 與 Observability Stack，本日不新增 Endpoint；新增的工程產物是 [Service Reliability Charter](docs/service-reliability-charter.md)。

## 內容

```text
Day4/DIY/
├── docs/
│   └── service-reliability-charter.md
├── app/                  # 繼承 Day3 的 FastAPI 與故障注入 endpoints
├── observability/        # Prometheus、Loki、Tempo、Alloy、OTel 設定
├── docker-compose.yml
└── README.md
```

Charter 定義：

- 服務、使用者與核心任務
- System boundary 與 dependencies
- User expectations 與 reliability dimensions
- 至少五種 known failure modes
- 目前可取得的 Metrics、Logs 與 Traces
- Availability 與 Latency 的初始練習目標
- Technical success、Task success 與 AI reliability open questions

## 執行方式

本日文件驗證不需要啟動 Docker：

```bash
cd Day4/DIY

test -f docs/service-reliability-charter.md
grep -n "Technical success" docs/service-reliability-charter.md
grep -n "Task success" docs/service-reliability-charter.md
grep -n "Open Questions" docs/service-reliability-charter.md
```

預期四個命令都成功，後三個命令會輸出相符行號。

若要重新執行 Day3 繼承的服務與故障實驗：

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

- [x] `docs/service-reliability-charter.md` 存在。
- [x] 已定義主要使用者與核心任務。
- [x] 已列出目前與未來的 System Boundary、Dependencies。
- [x] 已列出七種 Known Failure Modes。
- [x] 已記錄 Metrics、Logs、Traces 與目前的觀測缺口。
- [x] 已將 `99.5%` 與 `P95 < 300 ms` 標示為尚未驗證的練習目標。
- [x] 已區分 Technical Success 與 Task Success。
- [x] 已列出八個 AI Reliability Open Questions。
- [ ] 未啟動 Docker；Day4 沒有新增 Runtime behavior，繼承服務的執行結果未在本日重跑。

## 發現的問題與修正

1. **初始目標不是實測成績。** Charter 明確把 `99.5% request success rate` 與 `P95 < 300 ms` 標成 Hypothesis，避免把短時間 Lab 結果誤寫成 Production SLO。
2. **目前 Lab 還不是 AI Service。** LLM Provider、RAG、Tool Calling 與 AI Quality Evaluation 都保留為未來範圍或 `UNKNOWN`，沒有用預定架構冒充已完成能力。
3. **文件也需要驗收。** README 提供可重跑的 `test` 與 `grep` 命令，確認 Charter、Technical Success、Task Success 與 Open Questions 都存在。

## 證據邊界

Charter 中的 `99.5% request success rate` 與 `P95 < 300 ms` 是後續練習用 Hypothesis，不是本次驗證已達成的 Production SLO。

Day3 的本機實測結果只能證明特定環境與時間點的行為；正式 Availability、RTO、Data Durability 與 AI quality 仍標為未驗證或 `UNKNOWN`。
