# Day5 DIY — Reliability Responsibility Map

對應 [Day5/Day5.md](../Day5.md) 的實作。此目錄繼承 Day4/DIY 的 FastAPI、Observability Stack 與 Service Reliability Charter，本日不新增 Endpoint 或 Runtime behavior；新增的工程產物是 [Reliability Responsibility Map](docs/reliability-responsibility-map.md)。

## 內容

```text
Day5/DIY/
├── docs/
│   ├── service-reliability-charter.md   # 繼承 Day4
│   └── reliability-responsibility-map.md  # Day5 新增
├── app/                  # 繼承 Day3/Day4 的 FastAPI 與故障注入 endpoints
├── observability/        # Prometheus、Loki、Tempo、Alloy、OTel 設定
├── docker-compose.yml
└── README.md
```

Reliability Responsibility Map 把 Day4 Charter 裡的一項 User Expectation，拆成三種產出：

- DevOps Practices：協作與 feedback loop
- SRE Practices：可靠性量測與決策
- Platform Capabilities：可自助使用的共用能力
- Owners and Interfaces：誰負責、誰參與、透過什麼介面
- Evidence 與 Open Questions：明確區分已驗證與尚未驗證的部分

## 執行方式

本日文件驗證不需要啟動 Docker：

```bash
cd Day5/DIY

test -f docs/reliability-responsibility-map.md
grep -n "## User Expectation" docs/reliability-responsibility-map.md
grep -n "## Owners and Interfaces" docs/reliability-responsibility-map.md
grep -n "## Open Questions" docs/reliability-responsibility-map.md
```

預期四個命令都成功，後三個命令會輸出相符行號。

若要重新執行 Day3/Day4 繼承的服務與故障實驗：

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

- [x] `docs/reliability-responsibility-map.md` 存在。
- [x] 寫下一項明確的 User Expectation，並連回 Charter 對應章節。
- [x] 分別列出 DevOps、SRE 與 Platform Engineering 的具體產出。
- [x] 每項 shared capability 都有使用者與操作介面（見 Owners and Interfaces）。
- [x] 寫下 owner、contributors 與 collaboration interface。
- [x] 把未經驗證的 ownership、SLO 與 adoption 標成 `UNKNOWN` 或 Hypothesis。
- [x] 至少記錄一個不值得平台化的問題（見 Open Questions 第一項），避免過早抽象。
- [ ] 未啟動 Docker；Day5 沒有新增 Runtime behavior，繼承服務的執行結果未在本日重跑。

## 發現的問題與修正

1. **`Owners and Interfaces` 三欄目前都是同一個人。** 個人 Lab 沒有跨團隊組織，填表格容易變成自問自答的形式練習。文件裡特別註明這點，避免讓讀者誤以為表格本身就代表已經有分工。
2. **平台能力的「adoption」暫時無法驗證。** 文章強調平台要有使用者、要驗證 adoption，但本 Lab 只有單一使用者，所以誠實標成尚未驗證，而不是假裝已有多團隊採用。
3. **AWS us-east-1（2021-12-07）案例是文章引用的既有事件，本專案沒有重現。** Open Questions 只用它來說明「control plane 故障會拖慢 data plane 復原」的原則，並指出本專案目前沒有為此情境準備 fallback 觀測路徑，而不是宣稱已做過對應演練。

## 證據邊界

`docs/reliability-responsibility-map.md` 是文件層級的練習產物，證明「一項使用者期待可以拆成 DevOps／SRE／Platform 三種具體工程產出」，不代表：

- 這份 ownership 已被真實組織接受。
- Charter 中 `99.5%` 與 `P95 < 300 ms` 已被 production 流量驗證。
- Platform capabilities 已有除了作者以外的使用者。

以上三項在文件中皆已明確標示為待驗證或 `UNKNOWN`。
