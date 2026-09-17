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

2012 年 Knight Capital 的股市交易事故，是 Correctness 失敗的極端案例。一名工程師部署新程式時漏掉一台伺服器，讓那台伺服器上一段早已停用、本應被覆蓋的舊交易邏輯重新被觸發。系統技術上完全正常運作：request 進來、訂單送出、回應都合法，沒有任何 5xx。但送出的訂單本身是錯的，45 分鐘內對 148 檔股票下了大量非預期交易，最終虧損約 4.4 億美元。[Knight Capital 交易事故](https://en.wikipedia.org/wiki/Knight_Capital_Group#2012_stock_trading_disruption) Availability 全程正常，Correctness 徹底失守——這正是為什麼 `success=true` 不能只看 API 有沒有回應。

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

## ⑧ 今天記住的事：可靠性先有邊界，才有數字

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

## ⑨ 參考資料

- [Google SRE Book：Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Book：Production Services Best Practices](https://sre.google/sre-book/service-best-practices/)
- [Google SRE Book：Data Integrity](https://sre.google/sre-book/data-integrity/)
- [AWS：2017 us-east-1 S3 事故報告](https://aws.amazon.com/message/41926//)
- [GitHub：2018-10-21 Incident Report](https://github.blog/news-insights/company-news/october21-incident-report/)
- [GitLab：Postmortem of database outage of January 31 (2017)](https://about.gitlab.com/blog/postmortem-of-database-outage-of-january-31/)
- [Knight Capital Group — 2012 stock trading disruption](https://en.wikipedia.org/wiki/Knight_Capital_Group#2012_stock_trading_disruption)

## 下一篇：Day 07｜Technical Success ≠ Semantic Success

HTTP 200、schema valid、trace complete，都是有用的 evidence。

它們仍可能沒有回答使用者真正的問題。

---

> 這篇是 **Learning SRE for the AI Era** 系列的一部分。
>
> 我會從 SRE 的服務可靠性基礎開始，逐步探索當系統加入 LLM、RAG、Agent 與 GPU Infrastructure 後，如何讓 AI 系統不只可用，也能被觀測、評估、控制成本並安全演進。
>
> **Build → Trace → Break → Measure → Evaluate → Recover → Improve.**
