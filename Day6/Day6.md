# Day 06｜Reliability 到底是什麼？把「很穩」拆成五個能討論的問題

> GitHub：[darkstar1227/learning-sre-for-ai-era](https://github.com/darkstar1227/learning-sre-for-ai-era)

> **Reliability Is More Than Uptime: Availability, Latency, Correctness, Durability, and Recoverability**

**一句話先說：可靠性不是服務有沒有活著，而是使用者需要它時，能不能在可接受時間內拿到正確結果；資料出了事時，能不能證明找得回來。**

Day 3，我們看過幾種很不一樣的壞法：慢到 client 放棄、HTTP 500、PostgreSQL 連不上、container 直接停掉。

Day 4，我們在 Service Reliability Charter 裡寫了幾個看似熟悉的詞：`Availability`、`Latency`、`Correctness`、`Recoverability`、`Data durability`。

這些詞若只停在表格裡，和「系統要穩」沒有太大差別。都很正確，也都不夠用。

先看一個常見場景。

```text
使用者送出問題
        ↓
API 回傳 HTTP 200
        ↓
答案引用了過期文件
        ↓
使用者依答案做了錯誤決策
```

如果只看 HTTP status，這次 request 成功了。從使用者任務來看，它失敗了。

反過來也成立：資料庫短暫不可用，API 回傳 503。Availability 下降，但如果資料沒有被錯寫、備份可以還原，Correctness、Durability 與 Recoverability 是另外幾個仍須回答的問題。

可靠性不是單一分數，而是一組和使用者任務有關的屬性。今天先把它拆開。Day 7 才會處理更棘手的一題：技術上成功，是否真的完成了使用者任務？

## ① Reliability 的起點是使用者，不是 dashboard

Google 的 SRE 實務把服務水準指標的選擇，放在「使用者在乎什麼」之後，而不是「監控系統已經收得到什麼」之後。[Service Level Objectives](https://sre.google/sre-book/service-level-objectives/) 甚至記錄過一個很直白的例子：從 Gmail client 而不是 server 量測錯誤率與延遲，對可用性的評估明顯變差，才促成 client 與 server 兩端的改善。[Production Services Best Practices](https://sre.google/sre-book/service-best-practices/)

這個順序很重要。因為 server 看見的 200，不等於使用者看見的結果。

以我們的 AI 問答 Lab 為例，別急著問「P95 是多少」。先寫下使用者想完成什麼：

```text
使用者：提交一個問題
期待：在可接受時間內，收到可用且沒有捏造的回答
```

接著才問：哪幾種失敗會破壞這個期待？

| 使用者看到的狀況 | 主要受影響的維度 | `200 OK` 足夠嗎？ |
| --- | --- | --- |
| 頁面無法送出或 API 回 503 | Availability | 不夠 |
| 15 秒後才出現答案，前端已 timeout | Latency、Availability | 不夠 |
| 答案格式正確，內容卻答錯 | Correctness | 不夠 |
| 已儲存的對話紀錄消失 | Durability | 不夠 |
| 誤刪資料後無法在承諾時間內復原 | Recoverability | 不夠 |

這張表不是 SLO，也沒有神奇地讓系統變穩。它只做一件很實際的事：避免團隊拿一個健康檢查 endpoint，替五種不同的風險背書。

## ② Availability：需要時，服務能不能被使用？

Availability 是「服務可供使用的比例」。對 request/response 服務，常會以成功 request 的比例近似；Google SRE 也提醒，這個近似必須回到使用者觀點，並非把所有 HTTP request 一起除一除就結案。[Embracing Risk](https://sre.google/sre-book/embracing-risk/)

對 Lab 而言，以下是合理的起點：

```text
納入：使用者真的會呼叫的 /api/* request
成功：在既定條件下得到可用回應
失敗：5xx、client 已放棄的 timeout、或服務明確拒絕後無法完成任務
排除：內部 readiness probe、已知的測試流量、使用者取消的 request
```

這不是通用公式。`404` 要不要算失敗，取決於它代表「使用者輸錯網址」還是「我們本來就該提供的資源消失」。一個 DELETE request 回 `404`，在某些 idempotent API 裡甚至可以是可接受結果。

2017 年 AWS S3 在 `us-east-1` 的事故很適合提醒我們：服務不是只有自己的 API。一次原本要移除少量容量的操作，因輸入錯誤移除了更多伺服器，影響了 S3 的 index 與 placement subsystem，連帶讓 GET、LIST、PUT、DELETE 無法服務；當時狀態頁的管理介面也依賴 S3，無法照原本方式更新狀態。[AWS 的事故報告](https://aws.amazon.com/message/41926//)

Availability 問的不是「某個 process 還在不在」。它問的是：在這條依賴鏈上，使用者現在能不能完成要做的事。

## ③ Latency：答案太晚到，通常和沒到差不多

Latency 是使用者等待結果的時間。它有兩個容易被忽略的陷阱。

第一，server 的處理時間不一定等於使用者等待時間。DNS、網路、queue、frontend retry、streaming 的第一個 token，都可能在 server log 的計時之外。

第二，平均值很會掩飾問題。

```text
95 個 request：100 ms
5 個 request：10 s

平均：約 595 ms
```

平均不到一秒，讀起來沒有特別恐怖；那 5 位使用者不會這樣想。Google SRE 建議把 latency 當成分布處理，因為平均值會遮住 tail latency。[Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)

Day 3 的 slow request 實驗剛好說明了這件事：服務可能最後仍回 200，client 卻已經 timeout。此時不要在 incident 頻道爭論「server 到底算不算成功」。把兩個事實分開記錄：

```text
Server outcome：HTTP 200
Client outcome：timeout
```

兩者同時為真。若 SLI 只從 server 看，這條 request 的使用者體驗會被消音。

對生成式 AI，Latency 還常需要拆得更細：

```text
Time to first token（第一個 token 何時出現）
Time to complete（完整回答何時結束）
Tool / retrieval 等待時間
```

先記錄、先理解 workload，再決定哪些要成為正式指標。不要因為看過一張 dashboard，就替互動式聊天、批次摘要與 background ingestion 填同一個「可接受秒數」。

## ④ Correctness：回應成功，不代表回應正確

Correctness 問的是：服務是否回傳了正確的結果、正確的資料，或正確地完成計算。

這個維度會讓傳統 API 與 AI workflow 走向不同難度。

傳統 API 可能有相對明確的 oracle：付款金額是否正確、庫存是否真的扣減、同一筆資料讀回來是否一致。AI 問答則可能需要 evaluator、測試資料集、引用可追溯性，或人工審閱，才能判斷答案是否足以支援使用者任務。

但不要因此把 Correctness 推給「模型品質」後就不管。Google SRE 也把 correctness 視為所有系統都該關心的健康指標，只是它經常屬於資料或產品語意，而非基礎設施團隊單獨能保證的事。[Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)

今天只畫邊界，還不替 AI 答案宣告一個正確率：

```text
Technical success：API 收到 request、呼叫完成、回傳格式合法
Correctness：資料、計算與引用沒有違反已定義的規則
Task success：使用者是否真的完成目標（Day 7）
```

三者重疊，卻不是同義詞。

例如 RAG 回答有引用，不代表引用支持了答案；JSON schema 驗證通過，也不代表欄位裡的金額正確。把這些判斷混成一個 `success=true`，會讓後面的指標看起來很漂亮，排查時很痛苦。

2012 年 Knight Capital 的股市交易事故，是 Correctness 失敗的極端案例。該公司部署新程式時，讓 router 中原本不該使用的缺陷函式被觸發；router 無法辨識訂單是否已成交。系統技術上仍在運作：request 進來、訂單送出、回應流程沒有因 5xx 停下來。但送出的訂單本身錯了。美國 SEC 的調查指出，45 分鐘內 router 為 212 筆客戶訂單送出逾 400 萬筆 order，最後損失逾 4.6 億美元。[SEC：Knight Capital 的 market access rule 執法案](https://www.sec.gov/newsroom/press-releases/2013-222) Availability 沒有替 Correctness 背書，這正是為什麼 `success=true` 不能只看 API 有沒有回應。

## ⑤ Durability：寫進去的資料，還在不在？

Durability 關心資料在一段時間後是否仍被保留。它不是「資料庫現在連得上嗎」。

```text
資料庫連不上        → 主要是 Availability
資料讀得出來但內容錯 → Correctness / Integrity
昨天確認寫入的資料消失 → Durability
資料遺失後能否復原  → Recoverability
```

這四句很像，工程上的後果差很多。

2018 年 GitHub 的資料庫事故中，網站 metadata 出現不一致與延遲，但 repository data 沒有遺失；他們需要把多組資料庫追上並重放資料，才能回到正常狀態。[GitHub 的事故報告](https://github.blog/news-insights/company-news/october21-incident-report/) 這正是把「資料沒有消失」和「現在的資料是否正確且可用」拆開看的理由。

Durability 不應只寫成「有 backup」。備份是手段；要保護的是哪一類資料、允許遺失多久的資料、刪除操作是否可逆，才是問題本身。Google 的資料完整性指南也明確區分 replication、redundancy 與 recoverability：有複本不等於已經證明能復原。[Data Integrity](https://sre.google/sre-book/data-integrity/)

Lab 的資料量還小，仍值得先標出資料分類：

| 資料 | 若遺失，使用者受什麼影響？ | 目前證據 |
| --- | --- | --- |
| 對話 request／response 記錄 | 無法追查個別回答與故障 | 尚未持久化：UNKNOWN |
| 使用者帳號或權限 | 可能無法登入或錯誤授權 | 本 Lab 尚未實作：UNKNOWN |
| 觀測資料 | 事故後難以還原時間線 | 本機 stack，未驗證備援：UNKNOWN |

`UNKNOWN` 不是丟臉的欄位。把沒有做過的事寫成「已保護」，才是。

## ⑥ Recoverability：壞掉以後，能不能回來？

Recoverability 指的是：故障或資料損壞後，是否能在可接受的時間與資料損失範圍內恢復服務。

它至少包含兩個問題：

```text
多久能恢復？
最多能接受遺失多久的資料？
```

前者常用 RTO（Recovery Time Objective）討論，後者常用 RPO（Recovery Point Objective）討論。今天不替 Lab 設數字，因為我們還沒有量過 restore、也沒有和使用者確認可接受範圍。

避免一個經典誤會：

```text
有備份 ≠ 可復原
```

要能說「可復原」，至少需要留下證據：備份在哪裡、誰能取用、能還原到什麼時間點、還原後如何驗證資料與服務。沒有跑過 restore 的備份，比較像希望的壓縮檔。

2017 年 GitLab 一次資料庫事故就是這句話最直接的示範。工程師在排除異常複寫時誤刪了 production 資料庫目錄，事後才發現：五種原本設計的備份機制，幾乎沒有一種真正可用——`pg_dump` 因版本不符早已無聲失敗、LVM snapshot 沒有依排程執行、S3 備份為空。最終靠一份剛好在幾小時前手動觸發的 snapshot 搶救，仍遺失約六小時的資料，恢復過程耗時近 18 小時。[GitLab：Postmortem of database outage of January 31](https://about.gitlab.com/blog/postmortem-of-database-outage-of-january-31/) 備份存在，不代表任何一種都被驗證過能用；沒有定期演練 restore，等於直到事故當下才第一次測試。

AWS 在 2017 年 S3 事故後，除了調整防呆與容量移除的安全限制，也把縮短關鍵 subsystem 的 recovery time 列為改善方向；事故報告描述了 index 與 placement subsystem 依序恢復，以及下游服務還要處理累積 backlog 的過程。[AWS 的事故報告](https://aws.amazon.com/message/41926//)

恢復不是 container 重新亮綠燈就結束。還要確認：

```text
服務能接收新 request
依賴已可用
排隊中的工作如何處理
資料是否正確
使用者是否真的恢復任務
```

最後一項會在 Day 7 繼續拆解；先把它留在恢復驗證清單裡。

## ⑦ Lab：替一個 request 寫出「成功」的邊界

今天不需要改 application code，也不建立新的 DIY 專案。請在你的 `sre-for-ai-era` 專案建立：

```text
docs/
└── reliability-definition.md
```

把 Day 4 的 Service Reliability Charter 拿出來，先只選一個使用者任務，例如「送出問題後取得回答」。填入以下模板：

```markdown
# Reliability Definition

## User Task

使用者送出問題後，在可接受時間內取得可用回答。

## Request Boundary

- 入口：`POST /api/ask`（依你的實際 endpoint 修改）
- 起點：使用者送出 request
- 終點：使用者收到完整回應，或明確收到可採取下一步的失敗訊息
- 關鍵依賴：API、LLM provider、retriever、PostgreSQL（依實際架構修改）

## Availability

- 納入哪些 request：
- 成功定義：
- 失敗定義：
- 排除條件：
- 目前證據：

## Latency

- 從哪裡量到哪裡：
- 可接受 latency：假設，待使用者研究或實測驗證
- 是否區分 first token 與完整回應：
- 目前 evidence：

## Correctness

- 哪些規則可以自動驗證：
- 哪些需要 evaluator 或人工審閱：
- Technical success 與 correctness 如何分開記錄：
- 目前 evidence：

## Durability

- 要保留的資料：
- 可接受的資料遺失範圍：UNKNOWN
- 備份或保留機制：
- 已驗證的 restore：UNKNOWN

## Recoverability

- 可接受恢復時間：UNKNOWN
- 可接受資料損失時間範圍：UNKNOWN
- 已演練的恢復步驟：
- 恢復後的驗證方式：

## Open Questions

- 哪些 failure 對使用者是不可接受的？
- 哪一個依賴失敗會讓這項任務無法完成？
- 現有 Metrics、Logs、Traces 缺少什麼 evidence？
```

這份文件的驗收標準不是數字填得多漂亮，而是每一個「已做到」都能回指到 evidence：trace、log、測試紀錄、還原演練，或已知限制。還沒有證據，就填 `UNKNOWN` 或 `hypothesis`。

## ⑧ 同一筆 request，五個維度會給出五種答案

把一筆 request 放進五個格子，是避免「服務到底算不算壞掉」變成會議辯論最快的方法。

假設 `/api/ask` 收到一個查詢公司規範的問題。retriever 找到文件，模型在 1.2 秒回覆，API 回 `200`。隔天文件擁有者發現，那份文件已過期；回答引用了文件，也因此很自信地給了錯誤結論。

```text
request 進來                     → 有
HTTP response 回去                → 有，200
使用者等候時間                    → 1.2 秒
回答是否與當前規範一致            → 否
這筆回答是否必須保留以供追查      → 視產品需求而定
若發現錯誤，能否修正與重跑        → 尚未證明
```

別急著替它貼一個「成功」或「失敗」標籤。先逐項回答。

| 維度 | 這個案例的判斷 | 需要的證據 | 立刻該做什麼？ |
| --- | --- | --- | --- |
| Availability | 多半成功 | client 收到回覆、服務端成功記錄 | 不要因為 200 就停止調查 |
| Latency | 可能成功 | client 端或 edge 到完整回應的耗時 | 和互動式服務的等待預期比較 |
| Correctness | 失敗 | current policy、引用內容、回答內容 | 停止或修正受影響的回答路徑 |
| Durability | 尚未知 | request／response 是否被持久保存 | 確認是否能回溯受影響範圍 |
| Recoverability | 尚未知 | 更正資料、重新索引、重跑的紀錄 | 寫下修復與驗證步驟 |

這不是文字遊戲。若把 `200` 當成唯一成功條件，這次事件會被 dashboard 藏起來；若把所有維度都叫 outage，又會讓值班者不知道要先修哪一段。拆開之後，行動才會變得具體：服務端可能無須擴容，真正要處理的是文件版本、retrieval index 與受影響回答。

### 一個更不舒服、但更常見的案例

考慮另一種事件：資料庫切換期間，API 有 90 秒回 `503`。切換完成後服務恢復，資料也沒有遺失。

```text
Availability    → 失敗：這 90 秒內使用者不能完成任務
Latency         → 部分失敗：有些 client 等到 timeout
Correctness     → 未必失敗：資料沒有被寫錯
Durability      → 未必失敗：已確認的資料仍存在
Recoverability  → 不能只說成功：要看恢復時間與恢復後驗證
```

這種事件常被寫成「短暫服務異常，已恢復」。對 incident timeline 而言，它缺了最需要的資訊：多少使用者受影響？重試是否造成 backlog？切換前後的寫入有沒有重複或遺失？資料庫看似起來後，應用程式是否真的能完成一筆使用者任務？

可靠性維度的用處，就在於逼我們把這些問題問完。

### 不是每個維度都要用同一個時間窗

Availability 的事件通常以 minutes 或 requests 計。Durability 的答案可能要幾天後才知道，因為資料遺失常在還原、稽核或使用者回報時才浮現。Recoverability 更像一次演練或事故的完整紀錄，不能只截取「pod 已 Ready」那一秒。

```text
request 時間窗       → availability、latency
內容驗證時間窗       → correctness
資料保留時間窗       → durability
故障到復原時間窗     → recoverability
```

把五個維度壓進同一張一分鐘 dashboard，通常只會得到一張很擁擠的圖。較好的做法是保留共同的 `request_id`、`trace_id`、版本資訊與時間戳，讓不同時間窗的 evidence 可以在需要時被關聯。

## ⑨ 指標不是可靠性本身，而是可被反駁的證據

工程團隊很容易把「有 metric」誤會成「已經可控」。其實 metric 只是在替某個定義提供證據；定義錯了，圖畫得再漂亮也會把人帶錯方向。

先看兩個都很常見的指標：

```text
http_requests_total{status="200"}
http_request_duration_seconds
```

它們對 API 的供應狀態很有用，但回答不了：

- 這個 `200` 是否真的被 client 收到？
- 回應是否滿足產品定義的格式與內容規則？
- 這次回答用了哪個 prompt、model、retrieval index？
- 寫入事件是否在資料庫故障後仍然存在？
- 事故後是否真的完成過 restore？

因此今天不急著把五個維度全部做成 Prometheus alert。先做一件更基本的事：替每個維度寫出「能證明什麼」與「不能證明什麼」。

| Evidence | 可以支持的判斷 | 不能單獨支持的判斷 |
| --- | --- | --- |
| HTTP status | server 是否回覆特定狀態 | 使用者是否收到、內容是否正確 |
| server latency histogram | server 處理耗時的分布 | 網路、前端渲染與 client timeout |
| application log | 特定路徑是否執行、例外在哪裡 | 全體使用者影響比例 |
| trace | 一次 workflow 的步驟與依賴等待 | 答案是否符合真實世界 |
| evaluator result | 某套規則下的內容判定 | evaluator 自己是否正確 |
| backup job 成功訊息 | job 曾經跑完 | backup 一定可還原、還原資料正確 |
| restore drill 紀錄 | 某次演練的可復原性 | 未來所有事故一定能用同樣時間恢復 |

最後一列很容易被忽略。restore drill 是有力 evidence，不是永久保固。schema、資料量、權限、備份格式和依賴拓撲都會改變；演練也需要隨變更重做。

### 避免 metric 名稱替你下結論

下面這種寫法看似方便，實際上很危險：

```text
ai_answer_success_total
```

它把 technical completion、parser validation、groundedness、人工覆核與使用者任務完成混在一個名稱裡。半年後有人看到 success rate 99.9%，很可能以為答案品質也有 99.9%。

先把狀態拆開，名稱反而會誠實一些：

```text
ai_request_total{technical_status="success"}
ai_response_validation_total{result="pass"}
ai_evaluation_total{criterion="source_support",result="pass"}
ai_task_outcome_total{result="unknown"}
```

上面的名稱只是 schema 範例，不是要求你立刻產生所有 metric。尤其 `task_outcome` 很可能無法在 request 結束時知道。若沒有可信回饋來源，記成 `unknown` 比假裝 `success` 更接近工程事實。

### label 也有責任邊界

不要把 `request_id`、完整 prompt、使用者 email 或文件全文塞進 Prometheus label。這會造成高 cardinality，也可能把敏感內容送進不該承載它的系統。

比較安全的分工是：

```text
Metrics
  → 用低 cardinality 的狀態、路由、model route、版本或結果類別看趨勢

Logs / Traces
  → 用 request_id、trace_id、受遮罩後的細節追單筆事件

Evaluation dataset
  → 保存經權限與保留政策處理後、可重跑的案例與標註
```

這不是限制觀測，而是讓每一種儲存系統做它擅長的事。把所有細節都灌進 metric，通常既查不快，也留不久。

## ⑩ 實作：替 Lab 建立「可靠性證據地圖」

今天的實作不是再加一個 dashboard，而是讓 Day 2 到 Day 3 已有的 Metrics、Logs、Traces 和資料保護假設，開始回答同一個使用者任務。

以下步驟由讀者在自己的 `sre-for-ai-era` 專案執行。本文沒有建立、啟動或驗證 Day 6 的 DIY；命令與預期結果是給你自行對照的工作清單。

### 1. 建立資料夾與紀錄檔

在專案根目錄建立下列文件。若你已有同類文件，沿用既有位置即可，不必為了文章搬動架構。

```text
docs/
├── reliability-definition.md
├── reliability-evidence.md
└── recovery-drill.md
```

`reliability-definition.md` 使用上一節的模板。接著建立 `reliability-evidence.md`，先把每個聲明與 evidence 對上：

```markdown
# Reliability Evidence Map

## User Task

使用者送出問題後，在可接受時間內取得可用回答。

| Claim | Signal | Location | Status | Limitation |
| --- | --- | --- | --- | --- |
| API 能接受 request | HTTP request counter | Prometheus | observed | 只代表 server 看到 request |
| 回應沒有 server exception | structured application log | Loki | observed | 不代表答案正確 |
| workflow 有 retriever 與 model span | trace | tracing backend | observed | 不代表來源支持答案 |
| request 記錄可保留 | database record | PostgreSQL | hypothesis | 尚未做 restore |
| 資料可復原 | restore drill record | recovery-drill.md | UNKNOWN | 尚未演練 |
```

這張表的價值在於「Status」欄。`observed`、`hypothesis`、`UNKNOWN` 可以讓讀文件的人立刻知道哪些是看過的現象，哪些只是設計意圖。它也能避免 incident 時有人把 README 的願望當成已驗證能力。

### 2. 為單筆 workflow 保留可關聯的欄位

不管你用哪個 tracing SDK 或 logger，先在 application boundary 產生或接收 correlation ID。以下用 Python 示意資料模型，實際框架可調整：

```python
from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    workflow_name: str
    workflow_version: str
    prompt_version: str
    model_route: str
    retrieval_index_version: str


def new_request_context() -> RequestContext:
    return RequestContext(
        request_id=str(uuid4()),
        workflow_name="policy_qa",
        workflow_version="v1",
        prompt_version="grounded-qa-v1",
        model_route="primary",
        retrieval_index_version="policy-2026-09",
    )
```

這段 code 的重點不在 `dataclass`。它提醒我們，一次回答的可靠性判斷需要版本脈絡。發現錯答時，若只留下「模型很慢」或「API 回 200」，你無法判斷是 prompt 改動、index 更新、model route 切換，還是依賴服務讓 workflow 走了 fallback。

接著在 log 裡記錄狀態，不要只寫自然語言句子：

```python
event = {
    "event": "ask.completed",
    "request_id": context.request_id,
    "technical_status": "success",
    "workflow_status": "completed",
    "response_validation": "pass",
    "quality_status": "unknown",
    "task_status": "unknown",
    "prompt_version": context.prompt_version,
    "model_route": context.model_route,
    "retrieval_index_version": context.retrieval_index_version,
}
logger.info("ask completed", extra=event)
```

`quality_status` 與 `task_status` 保留 `unknown` 並不丟臉。它清楚告訴後續的 evaluator 或人工審閱：這次流程完成了，但內容還沒有被證明。

### 3. 讓 trace 與 log 指向同一筆工作

如果 tracing backend 已經提供 trace ID，把它一起放入結構化 log；若前端也會回傳 request ID，回應 header 或 body 可以保留它，讓使用者回報問題時有可查的索引。

```text
Client response
  └── request_id=req-123

Application log
  ├── request_id=req-123
  └── trace_id=4bf92f...

Trace
  ├── trace_id=4bf92f...
  └── spans=retrieve, model, validate
```

這個關聯能支援很實際的問法：

- 「這次使用者說答案錯，是哪份文件被取回？」
- 「這個 timeout 是卡在 retriever、model，還是 output parser？」
- 「某版 prompt 上線後，quality evaluator 的失敗是否增加？」

答案不在單一工具裡。Metrics 先告訴你趨勢，log 與 trace 才能帶你回到單筆事件。

### 4. 為一條失敗路徑寫出預期觀測

挑 Day 3 已做過或計畫做的 failure，例如「LLM provider timeout」。不要直接把故障當成一次炫技演示；先寫下應該在哪裡看見它。

```markdown
## Scenario: provider timeout

### Expected user outcome

- 使用者收到明確且可重試的失敗訊息，或按產品設計走 fallback。

### Expected technical evidence

- Metrics：timeout 或 dependency failure 計數增加。
- Logs：有 request_id、provider、timeout class，敏感 input 已遮罩。
- Trace：model span 標記 error 或 timeout，能看到等待時間。
- Response：technical_status 不得標為 success。

### What this does not prove

- fallback 回答一定正確。
- 使用者一定會重新嘗試。
- 依賴供應商的根因已被確認。
```

這份「預期觀測」比事後截圖有用。截圖只能證明你某次看到一張圖；預期觀測把可被反駁的假設寫在故障發生前，之後才能知道是哪一段沒有照設計運作。

### 5. 把 recovery 看成一條需要驗證的 workflow

即使你還不做正式還原，也可以先把 `recovery-drill.md` 寫成待執行程序。不要填入沒有跑過的完成時間。

```markdown
# Recovery Drill Plan

## Scope

- 資料：依你的資料庫與備份策略填寫
- 排除：cache、可重建 index、或其他不在本次範圍的資料

## Preconditions

- 備份位置、存取權限與版本已確認。
- 還原目標不是 production。
- 有驗證用的已知資料與帳號。

## Procedure

1. 記錄演練開始時間。
2. 依實際資料庫的官方還原程序，還原到隔離環境。
3. 驗證 schema、筆數範圍與已知資料。
4. 啟動只連向還原資料的應用程式副本。
5. 執行一筆正常使用者任務並保留 evidence。
6. 記錄完成時間、資料差異與無法完成的步驟。

## Result

- Status: NOT RUN
- Measured recovery time: UNKNOWN
- Measured data loss window: UNKNOWN
- Follow-up:
```

「依官方還原程序」不是偷懶。資料庫、版本與備份工具不同，硬抄另一個專案的 command 很容易在真正要救資料時造成二次事故。今天先定義驗證標準；選定技術後，再以該版本官方文件補上可執行命令。

## ⑪ 反例：五種常見的可靠性誤判

### 反例一：健康檢查綠燈，所以服務沒事

健康檢查通常只回答 process 是否活著、port 能否連線，或少量 dependency 是否可達。它不代表主要使用者路徑能完成。若 `/healthz` 只回字串，retriever 取到舊 index、權限服務拒絕使用者、LLM provider rate limit，都可能完全不影響它。

合理用法是把 health check 當成 routing 或快速偵測訊號，不能把它升格成 end-to-end SLI。

### 反例二：P50 很快，所以 latency 沒問題

P50 只描述中間那一位使用者。聊天式產品通常更在意 tail latency 與 first token，因為人會在空白畫面前等待。若 P50 300 ms、P99 30 s，值班者至少要知道後面那 1% 發生在哪個依賴與哪種 workflow，而不是用平均值安慰自己。

### 反例三：有引用，所以回答一定可信

引用可能過期、切錯段落、被錯誤解讀，或只和回答中的一小部分有關。Citation presence 是可觀測欄位，不是 truth proof。要把「有引用」升格成品質判斷，仍要檢查 source support、版本、範圍與資料新鮮度。

### 反例四：備份 job 成功，所以 RPO 與 RTO 已達成

備份 job 可能只備到部分資料、備到無法存取的位置，或依版本不相容而無法還原。即使能還原，所需時間與資料缺口也可能不符合產品需要。RPO、RTO 是和需求對齊的目標；backup job success 只是其中一條證據。

### 反例五：事故結束了，所以不用補資料

服務恢復後，真正困難的部分常剛開始：queue 裡的工作是否重複執行？使用者在錯誤期間的寫入是否需要補償？錯答是否已被使用者採用？cache 是否仍保有舊資料？若這些問題沒被驗證，incident 只能說「部分恢復」。

## ⑫ Reader Checklist：今天完成後應該留下什麼

請依自己的 Lab 實作，不要為了打勾填入未觀察過的結論。

```text
[ ] 我已選定一個使用者任務，並寫明 request 起點與終點。
[ ] 我已把 Availability、Latency、Correctness、Durability、Recoverability 分開定義。
[ ] 我已列出每一個維度目前有哪些 evidence，以及 evidence 的限制。
[ ] 我沒有把 HTTP 200 直接稱為任務成功或語意正確。
[ ] 我已保留 request_id 與 trace_id 的關聯方式。
[ ] 我已記錄 prompt、workflow、model route、retrieval index 等版本脈絡。
[ ] 我沒有把 prompt、完整使用者輸入或 request_id 放入 Prometheus label。
[ ] 我已為一種 failure 寫下預期的 Metrics、Logs、Traces 與使用者結果。
[ ] 我已把 restore 視為待演練項目；未演練處明確標為 UNKNOWN 或 NOT RUN。
[ ] 我知道下一步需要處理 semantic success，而不是替品質先填一個百分比。
```

### 本日驗收的界線

完成文件與程式碼範例，不等於服務已達到任何 production SLO。你至少可以確認的是：每個可靠性聲明是否有對應 evidence、每個未知是否沒有被包裝成事實，以及事故發生時你是否知道該到哪裡找證據。

若還沒有 Metrics、Logs 或 Traces，不要硬做一個空白 dashboard。先把 evidence map 的欄位留成 `NOT INSTRUMENTED`，再回到 Day 2 的 observability stack 補齊。可靠性工作不怕未知；怕的是未知被命名成綠燈。

## ⑬ 今天記住的事：可靠性先有邊界，才有數字

把 Reliability 壓成 uptime，會漏掉慢、錯、資料消失，以及回不來。

```text
Availability    → 需要時能不能使用？
Latency         → 結果來得及嗎？
Correctness     → 結果對嗎？
Durability      → 寫進去的資料還在嗎？
Recoverability  → 壞掉後能回到可用狀態嗎？
```

這五個問題不必全部套用到每個 service。靜態圖片 CDN 與支付帳務系統，需要的可靠性組合本來就不同；Google 的 SRE 文件也建議依服務類型與使用者需求選擇少數有代表性的指標，而不是蒐集所有量得到的數字。[Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)

下一篇會把最容易被偷換的一件事拆開：API 成功、資料正確，是否等於使用者任務成功？

## ⑭ 參考資料

- [Google SRE Book：Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Book：Production Services Best Practices](https://sre.google/sre-book/service-best-practices/)
- [Google SRE Book：Data Integrity](https://sre.google/sre-book/data-integrity/)
- [AWS：2017 us-east-1 S3 事故報告](https://aws.amazon.com/message/41926//)
- [GitHub：2018-10-21 Incident Report](https://github.blog/news-insights/company-news/october21-incident-report/)
- [GitLab：Postmortem of database outage of January 31 (2017)](https://about.gitlab.com/blog/postmortem-of-database-outage-of-january-31/)
- [SEC：Knight Capital market access rule 執法案](https://www.sec.gov/newsroom/press-releases/2013-222)

## 下一篇：Day 07｜Technical Success ≠ Semantic Success

HTTP 200、schema valid、trace complete，都是有用的 evidence。

它們仍可能沒有回答使用者真正的問題。

---

> 這篇是 **Learning SRE for the AI Era** 系列的一部分。
>
> 我會從 SRE 的服務可靠性基礎開始，逐步探索當系統加入 LLM、RAG、Agent 與 GPU Infrastructure 後，如何讓 AI 系統不只可用，也能被觀測、評估、控制成本並安全演進。
>
> **Build → Trace → Break → Measure → Evaluate → Recover → Improve.**
