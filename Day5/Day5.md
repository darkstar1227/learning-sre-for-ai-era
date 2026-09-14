# Day 05｜DevOps、SRE 與 Platform Engineering：別再把三種工作混成一個職缺

> GitHub：[darkstar1227/learning-sre-for-ai-era](https://github.com/darkstar1227/learning-sre-for-ai-era)

> **DevOps, SRE, and Platform Engineering: Three Different Problems, One Reliable Service**

**一句話先說：DevOps 改變團隊協作方式，SRE 用工程方法管理可靠性，Platform Engineering 則把共用能力做成可自助使用的內部產品。**

Day 4，我們替服務寫下第一份 Service Reliability Charter。

文件裡有使用者期待、系統邊界、Failure 定義，也有尚未驗證的可靠性目標。接著問題來了：

> 誰要把這些期待變成每天真的做得到的工程工作？

打開幾份職缺說明，答案可能是 DevOps Engineer、SRE、Platform Engineer，偶爾三個一起出現，像是徵才網站的關鍵字吃到飽。

但三者不是同義詞，也不是排成一條升級路線。

```text
DevOps                  → 改善開發與維運如何合作
SRE                     → 用工程方法管理可靠性風險
Platform Engineering    → 把共用能力做成內部產品
```

它們可以由不同團隊負責，也可能由同一群人同時實踐。真正該比較的不是職稱，而是問題、方法與產出。

---

## ① The Question：同一個服務，為什麼需要三種觀點？

假設昨天的 Charter 寫著：

```text
使用者期待：送出問題後能在可接受時間內取得正確回應

已知風險：
- API deployment 可能讓服務中斷
- PostgreSQL unavailable 可能讓 critical path 失敗
- LLM provider 可能 timeout
- Prompt 或 model 更新可能讓答案品質下降
```

這不是一個人換上三頂帽子就會自動解決的問題。

我們至少要回答：

1. 開發與維運如何共同交付變更，而不是在出事時互相丟 ticket？
2. 哪些可靠性風險值得投入工程成本？如何量測與取捨？
3. 每個團隊是否都要自己重做 deployment、observability、runtime 與 guardrails？

三個問題，剛好對應三種觀點。

```text
協作問題          → DevOps
可靠性決策問題    → SRE
重複建設問題      → Platform Engineering
```

別急著畫組織圖。名稱會隨公司改變，問題不會。

---

## ② Traditional SRE：三者到底差在哪裡？

### DevOps：先拆掉交付流程中的牆

DevOps 最適合被理解成一組文化、實踐與協作方式，而不是某一套工具，也不只是把 Ops 改名成 DevOps。

它要處理的典型問題是：

```text
Developer：我的程式在本機可以跑。
Operations：但上線、監控、備援和半夜告警都是我的事。
```

DevOps 希望把這條斷裂的責任鏈接回去：

- 開發團隊參與服務上線後的結果
- 維運需求提早進入設計與交付流程
- 用版本控制、自動化測試與 CI/CD 減少人工交接
- 讓 feedback loop 更短，問題更早被發現

它最重要的產出不一定是一個平台或一份 SLO，而是更快、更安全且能持續回饋的工作方式。

Etsy 在 2012 年那篇著名的 [Blameless PostMortems](https://www.etsy.com/codeascraft/blameless-postmortems/) 講的正是這件事：與其追究是誰按錯按鈕，不如回頭看「系統設計為什麼容許這個錯誤發生」。這種做法降低隱瞞問題的誘因，讓團隊能把焦點放在學習與改善系統；它不是一套工具，而是一種讓 dev 與 ops 真的共用同一份責任的文化。

```text
Plan → Build → Test → Deploy → Operate → Learn
  ↑                                      ↓
  └────────────── feedback ──────────────┘
```

如果部署失敗永遠只算 Ops 的問題，儀表板只有少數人看得懂，開發者也不知道 production 發生什麼事，那麼就算 Jenkins、Kubernetes 和 Terraform 都裝齊了，牆還是在。

### SRE：把「希望穩一點」改成可操作的決策

Google 將 SRE 描述成：把軟體工程的方法用在 operations 問題上。這也是 Day 4 的核心。

SRE 關心的不是服務能不能永遠不壞，而是：

- 使用者如何判斷服務成功？
- 我們要量測哪個 SLI？
- 目標可靠性是多少？
- 還剩多少 Error Budget？
- 現在該繼續發布，還是先處理可靠性風險？
- 哪些重複工作應該自動化，避免 Toil 持續增加？

```text
User Expectation
      ↓
SLI → SLO → Error Budget
      ↓
Release / Reliability Decision
```

DevOps 說「開發與維運要一起負責結果」；SRE 再往前一步，提供一套能討論可靠性的工程方法。

因此，SRE 常被視為 DevOps 理念的一種具體實作，但兩者不能直接畫上等號。

Error Budget 不是牆上的裝飾數字。[Google SRE Book — Embracing Risk](https://sre.google/sre-book/embracing-risk/) 描述的正是這種機制：Error Budget 用完後，即使新功能已經開發完成、測試通過，發布也要依既定政策暫停，直到可靠性回到目標之上。這才是「用工程方法管理可靠性」的意思——不是靠人情或職級喊停，而是先講好規則，讓數字說了算。

### Platform Engineering：把鋪路能力做成產品

當公司只有一個服務，團隊自己維護 CI/CD、observability 與 runtime，可能還撐得住。

當公司有五十個團隊，情況會變成：

```text
Team A 自己寫 deployment pipeline
Team B 自己接 metrics 與 logs
Team C 自己處理 secrets
Team D 再做一套幾乎相同的模板
```

這不叫自治，這叫五十次重播。

Platform Engineering 的工作，是把重複且高認知負擔的底層能力，整理成開發團隊能自助使用的 internal platform。常見產出包括：

- Service template
- CI/CD paved road
- Runtime 與 deployment API
- Observability defaults
- Secrets 與 identity 整合
- Developer portal 與文件

```text
Application Team
      ↓ self-service
Internal Developer Platform
      ├── Build & Deploy
      ├── Runtime
      ├── Observability
      └── Security Defaults
```

平台不是把所有工具集中放在同一個入口就算完成。它有使用者，也要處理 adoption、usability、reliability 與 feedback；換句話說，平台本身是一個產品。

### 一張表先收斂

| 觀點 | 主要問題 | 常見方法 | 代表性產出 |
| --- | --- | --- | --- |
| DevOps | 團隊如何共同且持續地交付與運作服務？ | 共享責任、自動化、短 feedback loop | 跨團隊工作方式、CI/CD、共同 ownership |
| SRE | 多少可靠性才符合使用者需求？如何管理風險？ | SLI、SLO、Error Budget、Toil reduction | 可靠性目標、告警、runbook、工程決策 |
| Platform Engineering | 如何讓團隊不必重做共同基礎能力？ | Product thinking、self-service、paved road | Internal Developer Platform、templates、APIs |

這張表是理解模型，不是職務邊界的國際標準。現實中三個圓會大量重疊。

---

## ③ 三者如何在同一個系統合作？

回到我們的 FastAPI SRE Lab。

假設團隊準備發布一個新的 `/ask` endpoint：

```text
Client
  ↓
FastAPI
  ├── PostgreSQL
  ├── Redis
  └── LLM Provider
```

### DevOps 觀點：縮短從修改到回饋的距離

團隊會問：

- 程式碼與設定是否都進版本控制？
- Pull request 是否會跑測試與安全檢查？
- 開發者能不能看到部署結果？
- 出現 production 問題時，資訊是否回到原團隊？

### SRE 觀點：定義成功，管理失敗

團隊會問：

- `/ask` 的 request success rate 與 latency 怎麼量？
- LLM timeout 算 dependency failure，還是整體 task failure？
- 哪些告警值得叫醒值班人員？
- 變更消耗 Error Budget 時，要不要暫停發布？

### Platform Engineering 觀點：把共同做法變成預設值

團隊會問：

- 新服務能不能從 template 建立？
- Pipeline、OTel、metrics 與 structured logs 能否預先接好？
- 團隊能不能自助部署，不必每次排隊找平台人員代操作？
- 預設能力能不能被安全地擴充，而不是逼所有服務長一樣？

三者的關係比較像：

```text
DevOps 提供合作與回饋方式
          ↓
SRE 提供可靠性目標與風險決策
          ↓
Platform 把可重複的做法產品化
          ↓
Application Team 更安全地自助交付
          └──────── feedback ────────↑
```

這不是單向命令鏈。平台的預設值需要 SRE 的可靠性需求，也需要 application team 的使用回饋。

### 真實世界：平台掛掉時，修復能力也可能一起掛掉

AWS 在 2021 年 12 月 7 日的 `us-east-1` 事件中，內部網路壅塞不只影響部分服務，也干擾 monitoring 與 deployment systems。部分既有 workload 仍能繼續執行，但建立新資源，以及既有 container instance 終止或失敗後的重新啟動，都可能受到影響；修復速度也因此被拖慢。

這代表：

```text
Application Data Plane 還能處理部分流量
                    ≠
Platform Control Plane 仍能觀測、部署與恢復
```

平台能力本身也是可靠性邊界。Platform Team 要提供能力，SRE 要把這些能力納入 failure model，使用平台的團隊則需要知道降級與逃生路徑。把三個責任都寫成「平台組處理」，只會讓事故發生時多一個聊天室可以互相 tag。

---

## ④ AI Era Extension：模型進來後，交界更擁擠了

傳統服務的變更，主要落在 code、configuration 與 infrastructure。

AI 系統還多了：

```text
Prompt
Model
Embedding
Chunking
Reranker
Tool schema
Evaluation dataset
Safety policy
```

部署成功，不代表行為成功。

### DevOps 延伸：交付的不只是程式碼

AI 團隊需要讓 prompt、model、evaluation 與 application code 一起進入可追蹤的 delivery loop。

```text
Change
  ↓
Test + Evaluation
  ↓
Deploy
  ↓
Online Evidence
  ↓
Learn
```

如果 Prompt 在網頁介面直接改、Model 在 console 手動切換，Git 顯示沒有變更，不代表 production behavior 沒有變。

### SRE 延伸：Technical Success 不等於 Task Success

HTTP 200、P95 latency 與 availability 仍然重要，但不夠。

```text
Technical Success
  ├── request completed
  ├── latency acceptable
  └── dependency available

Task Success
  ├── answer relevant
  ├── grounded in allowed data
  └── action completed safely
```

SRE 不必獨自決定「好答案」的定義，但需要和產品、ML、domain expert 一起把它變成可評估、可觀測、可處理的 reliability signal。

### Platform Engineering 延伸：從 Developer Platform 到 AI Platform

AI Platform 可能提供：

- LLM Gateway 與 provider routing
- Model serving
- Prompt 與 model registry
- Evaluation pipeline
- Trace、token、latency 與 cost observability
- Tool permission 與 secrets
- Dataset 與 experiment tracking

名稱可能是 MLOps、ML Platform、LLMOps、AI Infrastructure 或 AI Platform Engineering。先別為名詞開會三小時，先問團隊究竟需要哪個共用能力。

更重要的是，不要第一天就打造宇宙級平台。

```text
先有兩個團隊重複遇到的問題
        ↓
做出最小 paved road
        ↓
量測 adoption 與使用摩擦
        ↓
再決定要不要抽象下一層
```

沒有人使用的 self-service platform，只是一座有 README 的空城。

Spotify 自己開發、後來捐給 CNCF 的 [Backstage](https://backstage.io/) 提醒我們：平台遷移需要時間，工具做出來不代表 adoption 會自動發生。Spotify 的 [migration 經驗](https://engineering.atspotify.com/2020/6/tech-migrations-the-spotify-way) 也顯示，這類遷移可能從數週拉長到數月；平台團隊得持續量測使用率、修 friction，把它當一個要對使用者負責的產品經營，而不是完成一次性建置就結案。

---

## ⑤ SRE Lab：替一項可靠性需求分配三種產出

今天不安裝新工具。這次要把 Day 4 的 Charter 變成一張 **Reliability Responsibility Map**。

在 `sre-for-ai-era` 建立：

```text
docs/
└── reliability-responsibility-map.md
```

先選一項使用者期待：

> 使用者送出問題後，服務應在可接受時間內回傳可用答案。

接著填入以下模板：

```markdown
# Reliability Responsibility Map

## User Expectation

使用者送出問題後，服務應在可接受時間內回傳可用答案。

## DevOps Practices

- Application team 共同負責 deployment 與 production feedback。
- Pull request 必須通過 automated test 才能合併。
- 部署結果與 failure evidence 必須回到原開發團隊。

## SRE Practices

- 定義 request success rate 與 latency SLI。
- 將初始 SLO 標成 hypothesis，未經 production evidence 不宣稱已達標。
- 為 LLM timeout 與 PostgreSQL unavailable 準備診斷 evidence。

## Platform Capabilities

- 提供已接好 Metrics、Logs 與 Traces 的 service template。
- 提供可重複使用的 deployment pipeline。
- 讓團隊自助取得 dashboard 與 trace link。

## Owners and Interfaces

| Item | Accountable | Contributors | Interface |
| --- | --- | --- | --- |
| Application behavior | Application Team | Product、ML | Repository、on-call |
| Reliability target | Service Owner | SRE、Product | Charter、SLO review |
| Shared delivery path | Platform Team | Security、SRE | Platform API、docs |

## Evidence

- 文件路徑：`docs/reliability-responsibility-map.md`
- 對應的 Charter requirement：待填
- 已驗證能力：待填
- 尚未驗證：Production ownership、SLO、platform adoption

## Open Questions

- 現在真的有跨團隊重複需求，還是只有單一服務的問題？
- 誰能決定暫停發布？
- 平台故障時，由誰支援使用平台的團隊？
```

### 不要只填 Team Name

「Platform Team 負責平台」幾乎沒有資訊量。

至少要寫清楚：

```text
誰對結果負責？
誰提供能力？
透過什麼介面合作？
出事時 evidence 回到哪裡？
```

RACI 表可以輔助討論，但不要讓縮寫取代工程設計。介面不清楚時，多一欄字母救不了 production。

---

## ⑥ Evidence：怎麼知道這張圖不是文件 cosplay？

這一篇沒有新增 runtime behavior，因此 Evidence 不是漂亮的 dashboard，而是文件能否連回真實系統。

檢查三件事。

### 1. 每個可靠性需求都有下一步

```text
User expectation
  ↓
DevOps practice
  ↓
SRE measurement or decision
  ↓
Platform capability（如果值得共用）
```

不是每個需求都必須有 Platform 解法。只有一個團隊遇到一次的問題，先在服務內處理，通常比較便宜。

### 2. 每項能力都有使用者與介面

```text
Bad:
Platform Team owns observability.

Better:
Application team 透過 service template 啟用 OTel；
Platform team 維護 Collector 與預設 dashboard；
SRE 與 service owner 定義需要觀測的 reliability signals。
```

### 3. 假設與證據分開

目前可以確認的是：

- 文件存在
- 三種觀點各自對應到具體實踐
- responsibility、interface 與 open questions 已寫下

目前不能確認的是：

- Production 上真的有這些團隊
- 這份 ownership 已被組織接受
- 初始 SLO 已被 production traffic 驗證
- 平台能力真的有人採用

把 UNKNOWN 寫出來，比把組織想像成已經成熟更有用。

---

## ⑦ What I Learned：職稱不是可靠性機制

今天最重要的理解是：

> DevOps、SRE 與 Platform Engineering 可以互補，但沒有任何一個名稱會自動帶來可靠性。

公司可以沒有名為 SRE 的團隊，仍然實踐 SLO、Error Budget 與 Toil reduction。

公司也可以有一整排 SRE 職稱，卻仍然靠人工部署、模糊 ownership 和凌晨轉傳告警維生。

同樣地，Platform Team 不該變成新的 ticket queue。平台存在的理由，是降低 application team 的認知負擔，讓安全且可靠的做法更容易被採用。

```text
名稱       ≠ 能力
工具       ≠ 協作
平台       ≠ 一堆共用服務
文件       ≠ 已被接受的責任
```

真正能留下 Evidence 的，是清楚的使用者期待、可操作的工程方法、可自助的能力，以及出了問題之後仍能走完的 feedback loop。

---

## ⑧ Production Takeaway

如果這是真實 production system，我不會先問「我們需不需要成立 SRE Team」。

我會依序問：

1. 哪個使用者結果最需要被保護？
2. 現在最大的協作斷點在哪裡？
3. 哪個可靠性風險需要 SLI、SLO 或 Error Budget 來管理？
4. 哪些能力已被多個團隊重複建造，值得平台化？
5. 平台的使用者、介面、支援方式與成效指標是什麼？

接著才決定組織與職稱。

對 AI 系統也是一樣：別因為看到 LLM，就立刻成立一個包辦 GPU、prompt、evaluation、on-call 與資料治理的超級團隊。先畫出工作流、風險、責任與 feedback loop，再把真正重複的能力放進平台。

可靠性是共同結果，但共同負責不等於沒有人負責。

---

## ⑨ 本篇實作驗收

- [ ] 建立 `docs/reliability-responsibility-map.md`
- [ ] 寫下一項明確的 User Expectation
- [ ] 分別列出 DevOps、SRE 與 Platform Engineering 的具體產出
- [ ] 每項 shared capability 都有使用者與操作介面
- [ ] 寫下 owner、contributors 與 collaboration interface
- [ ] 把未經驗證的 ownership、SLO 與 adoption 標成 `UNKNOWN`
- [ ] 至少記錄一個不值得平台化的問題，避免過早抽象

---

## ⑩ 參考資料

- [Google SRE Book：Introduction](https://sre.google/sre-book/introduction/)
- [Google SRE Book：Software Engineering in SRE](https://sre.google/sre-book/software-engineering-in-sre/)
- [Google SRE Book：Embracing Risk](https://sre.google/sre-book/embracing-risk/)
- [Google Cloud：DevOps](https://cloud.google.com/devops)
- [Google Cloud：What is platform engineering?](https://cloud.google.com/solutions/platform-engineering)
- [CNCF Platforms White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
- [Backstage：What is Backstage?](https://backstage.io/docs/overview/what-is-backstage/)
- [Etsy Code as Craft：Blameless PostMortems](https://www.etsy.com/codeascraft/blameless-postmortems/)
- [AWS：Summary of the AWS Service Event in the Northern Virginia Region](https://aws.amazon.com/message/12721/)
- [Spotify Engineering：Tech Migrations the Spotify Way](https://engineering.atspotify.com/2020/6/tech-migrations-the-spotify-way)

---

## 下一篇：Day 06｜Reliability 到底是什麼？

我們已經知道 SRE 負責把可靠性變成工程問題。

但「可靠」仍然很容易被說成一句沒有邊界的好話。

下一篇會繼續拆解：

```text
Availability
Latency
Correctness
Durability
Recoverability
```

以及為什麼同一個服務，對不同使用者可能有完全不同的 Reliability 定義。

---

> 這篇是 **Learning SRE for the AI Era** 系列的一部分。
>
> 我會從 SRE 的服務可靠性基礎開始，逐步探索當系統加入 LLM、RAG、Agent 與 GPU Infrastructure 後，如何讓 AI 系統不只可用，也能被觀測、評估、控制成本並安全演進。
>
> **Build → Trace → Break → Measure → Evaluate → Recover → Improve.**
