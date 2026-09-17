# Day 04｜什麼是 SRE？可靠性不是零故障

> GitHub：[darkstar1227/learning-sre-for-ai-era](https://github.com/darkstar1227/learning-sre-for-ai-era)

**What Is Site Reliability Engineering? Reliability Is Not Zero Failure**

**一句話先說：SRE 用軟體工程方法管理服務可靠性，工作範圍遠超過監控與救火。**

Day 1，我們用 Trace 看見一次 AI Workflow。

Day 2，我們建立了有 Metrics、Logs 與 Traces 的 SRE Lab。

Day 3，我們親手製造 Slow Request、Timeout、HTTP 500、PostgreSQL unavailable 與 Container crash。

今天不再多裝一套工具。

今天要回答一個更麻煩的問題：

> 看得見故障之後，我們到底想把服務改善成什麼樣子？

---

## ① 服務正常，真的代表可靠嗎？

先看兩個情境。

```text
情境 1：
API container 正常運作。
/health 回傳 200。
CPU 只有 20%。

但使用者等待 15 秒才收到回應。
```

```text
情境 2：
API 回傳 HTTP 200。
LLM 也產生了回答。

但回答沒有根據知識庫內容，
使用者根據錯誤答案完成了錯誤操作。
```

哪一個算服務失敗？

答案可能是：**兩個都算。**

第一個情境中，Infrastructure 還活著，HTTP Request 也成功了，但使用者可能早已放棄等待。這正是 Day 3 的 Slow Request 實驗：Error Ratio 可以接近 0，P95 與 P99 Latency 卻已經惡化。

第二個情境更棘手。系統在技術上成功回應，使用者任務卻失敗了。這是 Day 1 留下的問題：

```text
Technical Success
        ≠
Task Success
```

如果只看：

```text
HTTP 200
CPU 20%
Container Up
```

兩個服務都「綠到發光」。

使用者則可能已經在 Slack 裡把你的服務罵到頭頂發光。

所以 SRE 要處理的問題，比「機器活著嗎」多一層：

> **服務是否持續提供使用者所期待的結果？**

---

## ② 什麼是 Site Reliability Engineering？

一個容易理解的版本是：

> **Site Reliability Engineering 是用軟體工程的方法，設計、運作與持續改善可靠服務的工程實踐。**

Google 將 SRE 描述為把 Operations 視為 Software Problem，並關注 Availability、Latency、Performance 與 Capacity。它要讓工程方法進入服務運作，不是替既有人工維運換一個比較潮的職稱。

把三個字拆開看：

| 關鍵字 | 含義 | 在 SRE Lab 的例子 |
|---|---|---|
| Site | 真正提供給使用者的服務 | FastAPI API、未來的 LLM Endpoint 與 RAG Workflow |
| Reliability | 服務持續符合使用者期待的能力 | 可用、夠快、結果正確、故障後可恢復 |
| Engineering | 用程式、系統設計、自動化與資料解決問題 | Docker Compose、Metrics、Trace、Runbook、Failure Injection |

這裡的 `Site` 不必真的只是一個網站。

它可以是：

```text
API
Database
Streaming Pipeline
Internal Platform
Model Serving
RAG Workflow
Agent System
```

只要它對使用者提供一項服務，就會遇到 Reliability 問題。

---

## ③ SRE 不是什麼？

SRE 的工作不只包含：

```text
- 監看 Dashboard
- 收到告警後手動重啟服務
- 只負責 Linux、Server 或 Network
- 為所有 Incident 背鍋
- 追求永遠 100% Availability
```

Dashboard 很重要。

但 Dashboard 只會告訴你發生了什麼，不會替團隊決定：

```text
多少失敗可以接受？
哪個使用者旅程最重要？
什麼情況需要 Paging？
應該先修 Reliability，還是先交付 Feature？
多一個 9 值得多少成本？
```

SRE 要做的是：

```text
- 定義可靠性的標準
- 建立可觀測性
- 降低人工作業與 Toil
- 自動化部署、回復與驗證
- 設計可安全變更的服務
- 建立 Incident Response 與學習迴圈
- 在可靠性、功能、成本與開發速度之間做取捨
```

傳統維運、DevOps、Platform Engineering 與 SRE 並不是互斥職稱。它們也可能使用相同工具。

差異不能只靠「這個人會不會寫 Terraform」判斷。

Day 5 會專門拆解它們的目標、工作方式與產出。

---

## ④ 為什麼 SRE 的目標不是零故障？

今天先記住這句：

> **可靠性要高到足以符合使用者需求，不必無限往上堆。**

### 100% 通常不是合理目標

複雜系統一定會變更，也一定有依賴。

```text
Application
  ↓
Database
  ↓
Network
  ↓
Cloud Provider
  ↓
第三方 API
```

每一層都可能失敗。

如果把目標設為「永遠不能出錯」，最簡單的達成方式可能是：

```text
不要部署
不要升級
不要推出新功能
最好也不要有使用者
```

可靠性瞬間非常穩定。

產品也順便失去存在的意義。

Google SRE 承認風險存在，從使用者需求出發設定 Service Level Objective，再用 Error Budget 管理可靠性與變更速度的取捨。

### 多一個 9，成本也會跟著增加

以下用固定 30 天、共 43,200 分鐘估算：

| 目標可用性 | 30 天可容許不可用時間 | 常見工程含義 |
|---|---:|---|
| 99% | 7 小時 12 分鐘 | 基本可用服務，容許較長復原時間 |
| 99.9% | 43 分 12 秒 | 需要成熟監控、值班與復原能力 |
| 99.99% | 4 分 19.2 秒 | 冗餘、Failover 與變更控制要求明顯提高 |
| 99.999% | 25.92 秒 | 高成本、高複雜度、非常嚴格的架構與流程 |

這張表是可用性百分比的算術換算，不代表所有服務都應採用相同窗口，也不代表只要買了 Load Balancer 就會自動得到五個 9。

一個只在上班時間使用的內部工具，偶爾中斷 10 分鐘，影響可能有限。

若要把它升級為跨區域高可用，可能需要：

```text
Multi-region Deployment
Database Replication
Global Load Balancer
Automated Failover
Failover Testing
更複雜的資料一致性設計
更完整的 On-call 與 Incident Process
```

不是不能做。

問題是：**使用者真的需要嗎？產品願意支付成本嗎？**

Stripe 為了把可靠性目標推到 99.9995%，決定自己寫一套取代 Envoy 的分散式 Proxy（[Building a Data Plane from Scratch](https://www.stripe.dev/blog/building-a-data-plane-from-scratch-stripes-own-high-performance-distributed-proxy)）。新架構把 CPU 用量砍了一半，但代價是整套 data plane 從此由 Stripe 自己維護、自己承擔所有邊界案例。多一個 9，不是換個設定值，往往是換一整層工程複雜度與長期維運責任。

2026 年 GitHub 一次長達 7 小時 47 分鐘的全站中斷（[The August 17 Outage, and the Work Ahead](https://github.blog/news-insights/company-news/the-august-17-outage-and-the-work-ahead/)）則是另一面：問題不是程式碼缺陷，而是容量規劃跟不上成長——月提交量從 14 億衝上 29 億。事後補救不是加更多硬體了事，而是重新設計 retry budget 與 timeout 策略。這說明可靠性投資也有先後順序，不是每一塊都能同時做到位。

---

## ⑤ Reliability 是 Product Feature

假設購物網站的結帳 API 一週掛一次。

這會直接影響產品，不只是 Infrastructure Team：

```text
使用者能不能完成付款
訂單會不會重複建立
客服會收到多少案件
公司會損失多少收入
使用者下次還敢不敢回來
```

Reliability 是一種 Product Capability。

它需要 Product、Development、SRE、Security 與 Business 一起回答：

```text
誰是使用者？
最重要的任務是什麼？
什麼樣的失敗不可接受？
要做到多可靠？
願意付出多少成本？
```

SRE 提供工程方法與資料，幫助團隊做出這些決策；它不是一個可以把所有風險丟進去的回收桶。

可以先用一張簡化圖理解：

```text
                  Reliability
                      ↕
Feature Velocity ↔ Product Value ↔ Engineering Cost
```

更高的可靠性通常需要更多備援、更多測試、更嚴格的變更控制與更高成本。

Reliability 不一定會拖慢開發。好的自動化、可觀測性與安全發布機制，能讓團隊更有信心地變更。麻煩的是沒有目標，卻不斷追加複雜度。

2026 年 Telstra 一次時間伺服器軟體缺陷造成的全國性中斷，直接說明可靠性從來不只是工程指標。這次故障影響超過六百萬用戶，讓部分區域火車全面停駛，還導致數百通緊急求救電話（Triple Zero）失敗或中斷，Telstra 事後得對其中之一逐一做安全確認（[Telstra outage exposes national vulnerability](https://postmortem.io/incidents/telstra--2026-07-08--nationwide-outage-time-keeping-server-defect/)）。一個機房裡的 time-keeping server 失效，最後量化成的不是 Error Rate，而是社會層級的實際傷害。

---

## ⑥ SRE 的六類實踐

Google SRE 的書與 Workbook 涵蓋 SLO、Monitoring、Toil、Automation、Release Engineering、Incident Response、Capacity Planning 等大量主題。

以下六類是**本系列為後續學習整理的地圖**，不是業界唯一或 Google 官方固定的六分類。

| SRE 實踐 | 要解決的問題 | 本系列會做到什麼 |
|---|---|---|
| Service Level | 怎樣才算可靠？ | SLI、SLO、SLA、Error Budget |
| Observability | 系統現在怎樣？為什麼異常？ | Metrics、Logs、Traces、Dashboard |
| Incident Response | 壞掉時如何降低影響？ | Alert、Severity、Runbook、Postmortem |
| Toil Reduction | 哪些重複人工工作應被消除？ | CI/CD、Automation、Runbook Automation |
| Capacity & Resilience | 流量增加或依賴失敗時怎麼辦？ | Load Test、Timeout、Retry、Fallback |
| Change Management | 如何安全修改 Production？ | Canary、Rollback、Model 與 Prompt Change |

### Service Level

先定義使用者在乎什麼，再決定如何衡量。

```text
SLI：實際量到什麼？
SLO：希望做到多好？
SLA：未達承諾時有什麼商業後果？
Error Budget：允許多少不可靠？
```

今天不會深入公式。Day 14 之後會把它們逐一拆開。

### Observability

Day 2 已經建立：

```text
Prometheus → Metrics
Loki      → Logs
Tempo     → Traces
Grafana   → Investigation Entry Point
```

Observability 讓我們能問系統問題。

但裝完工具不等於做完 SRE。若不知道哪個使用者行為最重要，再漂亮的 Dashboard 也可能只是昂貴的螢幕保護程式。

### Incident Response

故障無法完全消失，團隊需要：

```text
及早發現
正確分級
限制影響
有效溝通
快速恢復
事後學習
```

Day 3 的 `Baseline → Inject → Observe → Recover → Verify`，已經是這個思考方式的縮小版。

Vercel 定期在自己的 production 環境真的執行核心資料庫容錯轉移演練（[Preparing for the Worst](https://www.vercel.com/blog/preparing-for-the-worst-our-core-database-failover-test)），文中講得很直接：「除非這些計畫定期在真正的 production 負載上演練，否則毫無意義」。Disaster Recovery 文件寫得再完整，沒有真的按下切換按鈕驗證過，都只是一份還沒被測試過的假設。

### Toil Reduction

Toil 是重複、手動、可自動化，且會隨服務規模線性增加的工作。

例如每天手動 SSH 進機器清 Log，不是某種古老的可靠性儀式。

如果問題每天重複發生，SRE 會優先問：

> 能不能從系統根源消除，或至少安全地自動化？

### Capacity & Resilience

服務在一個 Request 下正常，不代表在一萬個 Request 下正常。

依賴今天成功，也不代表明天不會 Timeout。

這時需要 Load Test、Capacity Planning、Timeout、Retry、Circuit Breaker、Fallback 與 Graceful Degradation。

### Change Management

許多 Incident 不是硬體突然心情不好，而是 Change 帶進來的。

安全變更需要：

```text
Automated Test
Reproducible Build
Progressive Delivery
Canary
Rollback
Post-deployment Verification
```

到了 AI 系統，變更不只包含程式碼，還有 Model、Prompt、Retriever、Tool Schema、Evaluation Dataset 與 Safety Policy。

---

## ⑦ Day 1 到 Day 4，現在連起來了

```text
Day 01：看見 AI Workflow 的 Trace
   ↓
Day 02：建立可觀測的 SRE Lab
   ↓
Day 03：主動製造故障並觀察訊號
   ↓
Day 04：定義我們到底要保護什麼
```

前三天提供的是 Evidence。

今天補上 Decision。

沒有 Evidence，可靠性討論容易變成感覺。

沒有 Decision，Observability 只會累積更多圖表。

所以今天的 Lab 不新增 Endpoint，改成建立一份會影響後續設計的工程文件：

```text
Service Reliability Charter
```

---

## ⑧ 實作：建立第一份 Service Reliability Charter

本篇完成版放在本系列的[Github](https://github.com/darkstar1227/learning-sre-for-ai-era)：

```text
Day4/DIY/docs/service-reliability-charter.md
```
Charter 是服務可靠性的初始共識，不是 SLA 或固定不變的承諾。它用來記錄：

```text
服務是什麼
服務誰
關鍵任務是什麼
邊界在哪裡
哪些失敗不可接受
目前能觀察什麼
還有哪些未知風險
```

### Step 1：建立目錄與文件

```bash
mkdir -p docs
touch docs/service-reliability-charter.md
```

### Step 2：先定義 Service 與 User

不要從 CPU 開始。

先寫：

```markdown
## 1. Service Overview

- 服務名稱：AI SRE Lab API
- 服務用途：提供可觀測、可注入故障的 API，支援後續 AI Workflow 實驗
- 主要使用者：開發者、系列讀者與測試工具
- 核心使用者任務：提交請求並取得可理解、可追蹤的回應
```

如果無法說清楚使用者任務，就還無法說清楚 Reliability。

### Step 3：畫出 System Boundary

```text
Client
  ↓
FastAPI
  ├─ PostgreSQL
  ├─ Redis
  └─ Observability Stack
       ├─ Prometheus
       ├─ Loki
       └─ Tempo
```

同時要寫明不在目前範圍內的項目。

例如 Day 4 的 Lab 尚未真的整合 LLM Provider、Retriever、Vector Database 與 Tool API。把它們寫成未來依賴，不要假裝已經存在。

### Step 4：從使用者角度定義 Failure

至少列出五種 Failure Mode：

```text
Application Exception
Dependency Timeout
Dependency Unavailable
Container Crash
Configuration Error
Resource Exhaustion
Network Failure
```

每個 Failure Mode 可以繼續問：

```text
使用者看到什麼？
我們看得到什麼訊號？
如何限制影響？
如何確認恢復？
```

### Step 5：寫下目標，但不要把假設寫成成績

本篇範例會寫：

```text
Availability practice target：99.5% request success rate
Latency practice target：P95 < 300 ms
```

這兩個數字是**後續練習用的初始目標**，不是已達成的 Production SLO。

我們目前只有短時間的 Baseline 與故障實驗，沒有足夠的長期資料確認服務已經符合它們。

先誠實寫下 Hypothesis，比先發明一張綠色月報有價值。

### Step 6：驗證文件真的存在

從 `Day4/DIY` 執行：

```bash
test -f docs/service-reliability-charter.md
grep -n "Technical success" docs/service-reliability-charter.md
grep -n "Task success" docs/service-reliability-charter.md
grep -n "Open Questions" docs/service-reliability-charter.md
```

預期四個命令都成功，後三個命令會印出相符行號。

Markdown 文件沒有 Compile，不代表不需要 Verification。

---

## ⑨ Service Reliability Charter 完整模板

```markdown
# Service Reliability Charter

## 1. Service Overview
服務名稱：
服務用途：
主要使用者：
核心使用者任務：

## 2. System Boundary
入口：
主要依賴：
非核心依賴：
不在本服務負責範圍內的項目：

## 3. User Expectations
使用者期待：
可接受的回應時間：
不可接受的失敗類型：

## 4. Reliability Dimensions
Availability：
Latency：
Correctness：
Recoverability：
Data durability：

## 5. Known Failure Modes
Application failure：
Dependency failure：
Resource exhaustion：
Configuration error：
Network failure：

## 6. Initial Observability
Metrics：
Logs：
Traces：
Dashboards：

## 7. Initial Reliability Goals
Availability goal：
Latency goal：
Error handling goal：
Recovery expectation：

## 8. AI Era Extension
使用的模型：
是否使用 RAG：
是否有 Tool Calling：
Technical success 如何定義：
Task success 如何定義：
語意品質如何評估：
安全風險：
成本限制：

## 9. Open Questions
目前還不知道什麼？
未來需要驗證哪些假設？
```

Charter 應該隨實驗證據更新，不是填完就封印的表格。

---

## ⑩ AI Era Extension：Uptime 以外的 AI Reliability

傳統服務通常先問：

```text
服務是否可連線？
Request 是否成功？
Response 是否夠快？
資料是否正確？
故障後能否恢復？
```

Production AI 還要繼續問：

```text
Model 是否可用？
Retriever 是否取得相關資訊？
Tool 是否正確執行？
Response 是否有根據？
使用者任務是否完成？
輸出是否安全？
成本是否可接受？
```

取捨也變得更多：

```text
AI Reliability
      ↕
Quality ↔ Safety ↔ Latency ↔ Cost
```

例如：

- 使用更強的模型，可能提高品質，也增加 Latency 與 Token Cost。
- 加入 RAG Validation，可能提高 Groundedness，也增加 Workflow 複雜度。
- 增加 Provider Fallback，可能提高 Availability，也可能讓模型行為不一致。
- 加入人工審核，可能提高 Safety，也降低即時性與自動化程度。

### Operational Metrics

除了 API Availability、CPU、Memory 與 HTTP 5xx，後續可以逐步觀察：

```text
TTFT
Token Throughput
Provider Error Rate
Retriever Empty-result Rate
Tool-call Success Rate
Queue Backlog
Retry Amplification
Cost per Request
```

### Quality、Safety 與 Task Metrics

另一組指標包括：

```text
Task-success Rate
Groundedness Score
Safety Violation Rate
Instruction-following Score
Cost per Successful Task
```

但它們通常不能只靠即時 Infrastructure Telemetry 得到。

你可能需要：

```text
Golden Dataset
Human Review
Rule-based Check
Model-based Grader
Online User Feedback
```

而且 Model-based Grader 也需要用人工標註校準。不能因為另一個 LLM 說第一個 LLM 很棒，就當作宇宙已經完成 Peer Review。

### 不是所有品質問題都要 Paging

一次 Hallucination 不一定需要凌晨三點叫醒 On-call。

但以下狀況可能需要立即處理：

```text
LLM Provider 全面 Unavailable
Tool-call Failure Rate 短時間暴增
Queue Backlog 持續增加
Safety Violation 大規模擴散
Cost per Successful Task 異常上升
```

是否 Paging，仍應回到使用者影響、SLO 與明確的處置方式。

如果告警響了，但值班人員除了盯著它看什麼都不能做，那可能不是 Pager，是電子版的焦慮製造機。

---

## ⑪ 本篇實作驗收

```text
[ ] 已建立 Day4/DIY/docs/service-reliability-charter.md
[ ] 已定義服務的主要使用者與核心任務
[ ] 已畫出服務邊界與主要 Dependency
[ ] 已列出至少 5 種可能 Failure Mode
[ ] 已列出目前可取得的 Metrics、Logs 與 Traces
[ ] 已寫下第一版 Availability 與 Latency 練習目標
[ ] 已把目標標示為 Hypothesis，而不是已達成的 SLO
[ ] 已區分 Technical Success 與 Task Success
[ ] 已寫下至少 3 個 AI Reliability Open Questions
```

完成版已經放在 `Day4/DIY`。

如果你修改成自己的服務版本，請保留不知道的項目，直接寫：

```text
UNKNOWN
```

誠實的 UNKNOWN 是下一個實驗的起點。

虛構的 99.99% 只是一張很快會被 Incident 打臉的海報。

---

## ⑫ Production Takeaway

SRE 不承諾系統永遠不會失敗。複雜系統一定會失敗，工程方法能幫我們：

```text
降低失敗機率
限制影響範圍
縮短復原時間
驗證恢復結果
從每次失敗中改善系統
```

Day 1 到 Day 3，我們已經看過 Trace、Observability 與 Failure Injection。

今天建立的 Service Reliability Charter，把「我覺得服務應該可靠」整理成：

```text
可以討論
可以設計
可以衡量
可以驗證
可以取捨
```

的工程目標。

對 Production AI 而言，服務可用只是起點。我們還要確認 Workflow 是否正常、Model 是否穩定、輸出是否可信、安全，以及是否值得使用者依賴。

可靠性不是零故障，而是團隊知道要保護什麼，也知道願意為它付出多少。

---

## ⑬ 參考資料

- [Google Site Reliability Engineering](https://sre.google/)
- [Google SRE Book：Introduction](https://sre.google/sre-book/introduction/)
- [Google SRE Book：Embracing Risk](https://sre.google/sre-book/embracing-risk/)
- [Google SRE Book：Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Book：Eliminating Toil](https://sre.google/sre-book/eliminating-toil/)
- [Google SRE Book：Release Engineering](https://sre.google/sre-book/release-engineering/)
- [Google SRE Workbook：Error Budget Policy](https://sre.google/workbook/error-budget-policy/)
- [Google：Responsible AI Evaluation](https://ai.google.dev/responsible/docs/evaluation)
- [OpenAI：Evals Drive the Next Chapter of AI](https://openai.com/index/evals-drive-next-chapter-of-ai/)
- [Stripe：Building a Data Plane from Scratch](https://www.stripe.dev/blog/building-a-data-plane-from-scratch-stripes-own-high-performance-distributed-proxy)
- [GitHub：The August 17 Outage, and the Work Ahead](https://github.blog/news-insights/company-news/the-august-17-outage-and-the-work-ahead/)
- [Vercel：Preparing for the Worst — Our Core Database Failover Test](https://www.vercel.com/blog/preparing-for-the-worst-our-core-database-failover-test)
- [postmortem.io：Telstra Nationwide Outage (2026-07-08)](https://postmortem.io/incidents/telstra--2026-07-08--nationwide-outage-time-keeping-server-defect/)

---

## 下一篇：Day 05｜DevOps、SRE 與 Platform Engineering

三者都談自動化、交付與系統運作。

也都可能同時出現在同一份職缺說明裡，讓人懷疑 HR 是不是把關鍵字當火鍋料全倒進去了。

但它們解決的問題、工作方式與主要產出並不完全相同。

下一篇會比較：

```text
DevOps
SRE
Platform Engineering
```

也會延伸到 AI Platform Engineering：當企業開始建立 LLM Gateway、Model Serving、Prompt Registry、Evaluation 與 Observability Platform，Platform Team 和 SRE 又會在哪裡交會？
