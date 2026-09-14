# Reliability Responsibility Map

> Status: 練習用文件。本文件釐清「誰對結果負責、誰提供能力、透過什麼介面合作」，不是已被組織正式採納的 RACI 決策。

## User Expectation

使用者送出問題後，服務應在可接受時間內回傳可用答案。

（對應 [Service Reliability Charter](service-reliability-charter.md) 第 3 節 User Expectations：「正常 request 取得格式明確且可理解的 response；異常時得到有限時間內的明確錯誤，而不是無限等待」）

## DevOps Practices

- Application team 共同負責 deployment 與 production feedback：新增或修改 endpoint 後，同一個團隊要看得到 metrics、logs 與 trace，而不是丟給另一組人維運。
- Pull request 必須通過 automated test 才能合併；本專案目前的驗證方式是 `docs/` 與 `app/` 的 grep/curl smoke check（見 README）。
- 部署結果與 failure evidence 必須回到原開發團隊：Day 3 的故障注入實驗（Slow Request、Timeout、500、PostgreSQL down、SIGKILL、OOM）都留有可重跑的觀測證據，而不是「修好就結案」。

## SRE Practices

- 定義 request success rate 與 latency 為第一個 SLI 候選；分母尚未決定是全部 HTTP requests 還是只計 `/api/demo`（見 Charter Open Questions #1）。
- 將 `99.5%` 與 `P95 < 300 ms` 標成 Hypothesis：這是練習用初始目標，未經 production evidence 驗證，不宣稱已達標。
- 為 LLM timeout 與 PostgreSQL unavailable 準備診斷 evidence：對應 Charter 第 5 節 Known Failure Modes 中的 Dependency timeout 與 PostgreSQL unavailable，兩者都已有 metric、log 與 trace 可查。

## Platform Capabilities

- 提供已接好 Metrics、Logs 與 Traces 的 service template：本專案的 `app/metrics.py`、`app/logging.py`、`app/telemetry.py` 與 `observability/` 設定即是最小版本。
- 提供可重複使用的 deployment pipeline：目前是 `docker compose up -d --build`（見 `docker-compose.yml`），尚未有跨團隊共用的 CI/CD pipeline，這件事本身就是一項 UNKNOWN。
- 讓團隊自助取得 dashboard 與 trace link：Grafana 已接 Prometheus、Loki、Tempo 三個 datasource，但目前只有一人使用，adoption 尚未被驗證。

## Owners and Interfaces

| Item | Accountable | Contributors | Interface |
| --- | --- | --- | --- |
| Application behavior | Application Team | Product、ML | Repository、on-call |
| Reliability target | Service Owner | SRE、Product | Charter、SLO review |
| Shared delivery path | Platform Team | Security、SRE | Platform API、docs |

在這個個人 Lab 裡，三欄目前都是同一個人；保留完整表格是為了練習「就算角色重疊，責任與介面仍要寫清楚」，而不是把所有欄位都填「我自己」就當作完成。

## Evidence

- 文件路徑：`docs/reliability-responsibility-map.md`
- 對應的 Charter requirement：[Service Reliability Charter](service-reliability-charter.md) 第 3 節 User Expectations、第 7 節 Initial Reliability Goals
- 已驗證能力：Metrics、Logs、Traces 三條 observability 路徑存在，且 Day 3 故障注入實驗可重跑並留下對應證據
- 尚未驗證：Production ownership、SLO（`99.5%`、`P95 < 300 ms` 仍是 Hypothesis）、platform adoption（目前只有單一使用者）

## Open Questions

- 現在真的有跨團隊重複需求，還是只有單一服務的問題？目前只有一個 Lab 服務，尚未出現第二個團隊重複建置相同能力，因此「值得平台化」暫時是 UNKNOWN，不預先假設需要正式 Platform Team。
- 誰能決定暫停發布？本 Lab 尚未定義 error budget policy 與對應的 release-gate 流程。
- 平台故障時，由誰支援使用平台的團隊？參考 AWS 2021-12-07 us-east-1 事件：control plane（部署、監控工具）本身故障時，會拖慢對 data plane 問題的診斷與復原，本專案目前沒有為這種情境準備獨立的 fallback 觀測路徑。
