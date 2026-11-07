# Day 09｜什麼是一個 Service？先畫出邊界，才知道故障影響哪裡

> GitHub：[darkstar1227/learning-sre-for-ai-era](https://github.com/darkstar1227/learning-sre-for-ai-era)

> **先講結論：**Service 是為使用者完成一項工作所需的系統邊界，也包含對結果、依賴與失敗行為的責任。

Day 8 把 AI 系統的 Reliability、Quality、Safety 分開看。接下來要談 failure model，得先回答一個更基本的問題：故障發生時，我們口中的「服務」到底是哪一段？邊界沒畫清楚，SLO、on-call、告警和事後檢討都很容易各講各的。

## ① 從一條熟悉的請求開始

傳統 Web API 的圖通常長這樣：

```text
Client
  ↓
API
  ├── DB
  └── External API
  ↓
Response
```

使用者看見的是「查詢訂單」或「新增預約」；實際上，API 可能要驗證身分、讀資料庫、呼叫付款或物流服務，才有辦法回應。

若把 Service 理解成「這個 API process 還活著」，很快會遇到盲點：process 正常、HTTP 200 也正常，資料庫可能已回傳舊資料，外部付款服務可能拒絕請求，或最後回覆的內容根本沒有完成使用者要做的事。

在 SRE 的語境裡，Service 要說清楚使用者要完成什麼工作、請求會穿過哪些依賴，以及依賴失敗時系統怎麼回應。

畫出邊界，是為了在 incident 發生時判斷使用者受影響的訊號與處理責任。

## ② Service 的邊界不是網路拓撲圖的外框

同一個元件可以同時出現在不同 Service 的邊界裡。

以「查詢訂單」為例，訂單 API 對 App 團隊是一個 Service；資料庫團隊提供的 PostgreSQL 也是另一個 Service；付款供應商則是外部 Service。它們有各自的使用者、契約與責任人，但一筆使用者請求會把它們串成一條路徑。

```text
使用者要查訂單
  ↓
Order API ──讀取──→ PostgreSQL
  │
  └──查詢──→ Payment Provider
```

這裡有兩個容易混在一起的概念：

| 名稱 | 問的問題 | 例子 |
| --- | --- | --- |
| 元件（component） | 這是什麼程式、資料庫或基礎設施？ | `order-api` pod、PostgreSQL instance |
| Service | 它替誰提供什麼能力，失敗時誰承擔結果？ | 「使用者能查到正確訂單狀態」 |

一個 Service 可由很多元件組成；一個元件也可能同時服務多條使用者流程。把兩者畫上等號，最常見的後果是只監測 container health，卻沒發現使用者已經查不到正確結果。

GitHub 在 2026 年 9 月的一次事故中，內部資料清理工作把權限資料庫主節點的連線數寫到用盡。當時唯一被監看的健康訊號是 replica 延遲，而 replica 延遲全程正常；安全機制沒有察覺主節點正在逼近極限，直到請求開始大量逾時。監測的元件「健康」，使用者能不能登入、建 issue 卻早已不健康。[GitHub 事故報告](https://www.githubstatus.com/history)

Google 的 SRE 書也把服務視為有使用者期待的行為，而非單一機器：SLI 與 SLO 要先從使用者在意的行為出發，再決定如何量測。[Google SRE Book：Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)

## ③ 依賴關係要畫到「無法完成工作」的位置

不是每個呼叫失敗都同樣嚴重。關鍵在於它對對外能力的影響。

```text
Order API
  ├── PostgreSQL：訂單資料的必要依賴
  ├── Payment Provider：付款狀態的必要依賴
  └── Recommendation API：可選依賴，失敗時可省略推薦區塊
```

這三條箭頭看起來很像，行為卻不同：

- PostgreSQL 無法讀取時，系統不能假裝訂單存在，應明確失敗或提供已知的受限讀取模式。
- Payment Provider 逾時時，不能把「查不到」寫成「未付款」；可能要顯示暫時無法確認，或改由背景工作補查。
- 推薦系統掛掉時，訂單頁仍可用，只是少了推薦商品。

dependency map 除了列名稱，也要寫下失敗時的預期行為與可觀測訊號。

| 依賴 | 為何需要 | 失敗時的預期行為 | 可觀測訊號 |
| --- | --- | --- | --- |
| PostgreSQL | 讀取訂單資料 | 回受控錯誤，不回傳猜測資料 | query error、latency、資料庫連線狀態 |
| Payment Provider | 顯示付款狀態 | 明示狀態暫不可確認，排入補查 | dependency timeout、補查 backlog |
| Recommendation API | 推薦商品 | 降級為不顯示推薦 | fallback rate、dependency error |

「預期行為」要在設計階段寫進 dependency map，而非 incident 後才補上。若團隊沒有決定 fallback，程式通常會等到 timeout、丟 500，或回一份看似完整但其實不可信的資料。

## ④ AI workflow 的 Service path 更長

AI 應用常被包成一個 `/ask` endpoint，實際的服務路徑卻比傳統 API 長得多：

```text
Client
  ↓
Gateway
  ↓
Prompt / Policy
  ↓
Retriever ──→ Vector DB
  ↓
Model ──→ LLM Provider
  ↓
Tool Executor ──→ Internal / External tools
  ↓
Validator
  ↓
Response
```

其中每一段都可能是另一個 Service，也可能是同一個團隊維護的元件。方塊數量不決定 Service boundary；是否要對契約與風險負責，才是判斷依據。

以公司差旅問答為例，使用者問「國際機票需要誰核准？」：

```text
Question
  ↓
Retriever 找政策文件
  ↓
LLM 依文件產生答案與引用
  ↓
Validator 檢查引用是否允許、格式是否符合 contract
  ↓
Answer
```

這條路徑至少有四種不同的失敗：

| 發生位置 | 使用者可能看見的結果 | 不該草率下的結論 |
| --- | --- | --- |
| Retriever | 找不到正確政策 | 「模型不會回答」 |
| Vector DB | 檢索逾時 | 「LLM provider 壞了」 |
| LLM Provider | 429、5xx 或 latency 增加 | 「RAG 的資料品質下降」 |
| Validator | 擋下不允許的引用或越權 action | 「API 成功就代表任務成功」 |

Day 8 的三條軸在這裡仍然成立。Provider timeout 是 Reliability 問題；引用無關文件卻自信作答是 Quality 問題；Agent 嘗試執行未授權操作則是 Safety 問題。它們可能同時發生，也可能只發生其中一種。別把整條 workflow 壓成 `success: true`。

## ⑤ 外部供應商仍是 dependency

「模型 API 回 200」不等於 AI Service 完成工作。同樣地，「我們用的是外部模型」也不等於所有可靠性責任都能交出去。

團隊無法控制 LLM provider 的內部系統，仍可決定自己的呼叫方式與失敗策略。包含 timeout、可重試的錯誤、rate limit 預算、資料不足時的拒答，以及 provider 不可用時要降級還是停止服務。

外部依賴出問題時，修復並不總是只靠「等待對方恢復」。AWS 在 2021 年 12 月 `us-east-1` 事件中提到，內部網路受影響後，monitoring 與 deployment systems 也受影響，讓排查與修復在能見度降低的狀態下進行。[AWS 的事件報告](https://aws.amazon.com/message/12721/) 監控、部署與身分驗證等 control plane 能力，同樣應出現在 dependency map；它們壞掉時，資料面可能還在處理部分流量，恢復能力卻已經變弱。

對 AI workflow 而言，還要額外問幾個問題：

- LLM provider 遇到 rate limit 時，使用者得到的是明確的稍後再試，還是無限重試？
- Retriever 沒有足夠 context 時，系統能否誠實拒答？
- Tool executor 不可用時，Agent 會不會捏造「已完成」？
- policy 或 validator 故障時，預設是 fail open 還是 fail closed？不同風險的答案不會一樣。

阻擋付款與顯示推薦商品的風險不同，故障預設值也應不同。把這個選擇寫下來，才能討論與測試。

## ⑥ 從使用者視角畫一條 critical path

複雜系統不需要第一天就畫出全公司的服務地圖。先挑一個使用者工作，畫出完成它所需的最短路徑。

```text
使用者取得「有來源、符合權限」的差旅政策答案
  ↓
Gateway 接受並驗證請求
  ↓
Retriever 取回允許的政策文件
  ↓
LLM 產生可解析的回覆
  ↓
Validator 驗證來源與權限
  ↓
回傳答案或明確說明無法完成的原因
```

這條 critical path 讓量測有對象、告警有上下文，也能及早討論 provider 故障或資料不足時的降級方式。這些是產品與風險決策，不是 SRE 一個人替大家決定。

Google 也提醒，服務間的 production dependencies 會形成巢狀關係；上游服務的放置與效能要求，會受下游依賴限制。[Google SRE Book：Developing Software for Complex Machines](https://sre.google/sre-book/software-engineering-in-sre/) 這也是為什麼只看自己服務的 CPU、memory 或 container restart 次數，通常不足以判斷使用者路徑是否健康。

## ⑦ 先分清楚「看得到」與「量得到」

先畫出 Service boundary，再挑 SLI。不是所有 trace 裡看得到的欄位，都已經是能用來管理可靠性的訊號。

以 `/ask` 為例，下面幾種狀態都可能出現在 telemetry：

| 訊號 | 可以先量什麼 | 還不知道什麼 |
| --- | --- | --- |
| Gateway | request rate、5xx、end-to-end latency | 低延遲是否代表答案有用 |
| Retriever | retrieval latency、empty-result rate | 找到的內容是否真的支持回答 |
| LLM Provider | timeout、429、token usage | 模型輸出是否正確或安全 |
| Validator | block rate、format failure rate | block 是精準攔截還是誤擋 |
| Tool Executor | execution success、denied action count | 工具成功執行是否完成使用者任務 |

前一欄是可操作的候選 SLI；後一欄需要 golden dataset、抽樣 review 或任務完成證據，才能用於判定。缺少這些證據時，就標成 `UNKNOWN`，不要用一個方便取得的 proxy 假裝它已被量測。

```text
retrieval latency 正常
            ≠
retrieved context 足以支持答案

tool execution success
            ≠
使用者任務已安全完成
```

可觀測性讓我們看見系統狀態；SLI 則是經過定義、能對應使用者期待並支撐決策的量測。Day 10 開始拆 failure 時，這個區別會很有用：有些訊號告訴我們哪裡壞了，有些訊號才告訴我們使用者是否真的受影響。

## ⑧ 不要把責任邊界誤寫成 blame boundary

畫出依賴，是為了讓每個 Service owner 清楚自己的契約、可觀測性與降級行為。

較好的分法是：每個 Service owner 對自己的契約、可觀測性和已知降級行為負責；使用它的團隊則對「把這個依賴放進使用者路徑後，自己的 Service 如何失敗」負責。兩邊都要做事。

例如 LLM provider 429 時，provider 負責恢復其服務；應用團隊仍要決定 retry policy、排隊上限、使用者訊息與是否切換備援。若每一層都只說「那是下游的問題」，最後使用者看到的只會是自己的問題。

這也是 Service boundary 能當共同語言的原因：產品能說清楚哪個使用者工作最重要；開發者能說清楚 contract；SRE 能把可用性、延遲、依賴與降級行為變成可觀察的訊號；安全或領域專家能界定哪些操作絕不能 fail open。

Google 的 SRE Book 也把這件事寫進制度：postmortem 的目的是釐清根因、訂出可執行的預防措施，並作為全公司的學習機會。Service boundary 與依賴責任要先畫清楚；否則事後檢討容易變成追究個人責任，系統問題反而沒有被修正。[Google SRE Book：Postmortem Culture](https://sre.google/sre-book/postmortem-culture/)

## ⑨ DIY：替一個使用者工作畫 Service boundary

這個 DIY 不需要先寫程式。挑一個你現在的 API 或 AI workflow，花 20 分鐘把它畫成一條使用者路徑。這個練習要找出使用者要完成什麼，以及中間卡住時系統會怎樣。完整架構文件不在本次範圍。

### Step 1：用一句話寫下對外能力

不要寫「RAG service」或「訂單 API」。試著寫成使用者結果，例如：

```text
已登入的員工可以查到有來源、符合權限的差旅政策答案。
```

這句話就是你暫時要守住的 Service contract。契約除了回傳文字，也要包含來源與權限。

### Step 2：從 client 畫到 response

沿著一個 request 寫下它經過的元件。先畫最短路徑即可：

```text
Client → Gateway → Retriever → Vector DB → LLM Provider → Validator → Response
```

每一個方塊旁邊補三個欄位：owner、必要或可選、失敗時的預期行為。若你寫不出最後一欄，不必硬湊答案，直接標 `UNKNOWN`。這表示失敗時的預期行為尚未定義。

### Step 3：挑一個 dependency failure 預演

例如假設 LLM provider 回 429，依序回答：

1. 使用者目前會看見什麼？
2. 系統會重試、排隊、降級，還是直接拒絕？上限是什麼？
3. 哪個 trace、log 或 metric 能告訴你這件事正在發生？
4. 這是 Reliability、Quality、Safety 中的哪一條問題？是否需要 pager？

把答案寫進 dependency map。若答案是「不知道」，一樣保留。它比在 incident 當下才發現沒人知道更有用。

### Step 4：找一個不能當 SLI 的訊號

從你的圖上挑一個容易量到、卻不能直接代表使用者結果的數字，例如 token usage、retrieval latency 或 tool execution success。替它寫下缺少的證據，再標為 `UNKNOWN`。這一步用來記錄 proxy 與使用者結果之間仍缺少的證據。

做完後，你應該能拿出一張含使用者結果、依賴、失敗預期與候選訊號的圖。這張圖記錄的是目前的設計假設。壓力測試與 incident drill 仍需另外進行；Day 10 分析 `Fault → Error → Failure` 時會以它作為共同座標。

## ⑩ 把 Service contract 寫成團隊能討論的資料

dependency map 很適合放在白板，但白板不會在 deployment 時提醒你漏了什麼。當服務開始有多個 owner、版本與降級路徑時，可以把最重要的假設寫成靠近程式碼的文件。它不必一開始就變成正式規格系統；先讓值班的人找得到、讀得懂即可。

以下是一份刻意簡化的範本。欄位不是標準，也不是要讀者照抄，而是把 Day 9 一直在問的問題固定下來。

```yaml
service: travel-policy-answer
owner: people-platform
user_job: >
  已授權的員工可查詢現行差旅政策，取得可追溯的答案；
  資料不足或系統無法確認時，回傳明確狀態，不編造內容。

request_contract:
  authentication: required
  response_deadline_ms: 5000
  required_response_fields:
    - answer_status
    - sources
    - request_id

dependencies:
  policy_index:
    criticality: required
    owner: knowledge-platform
    failure_behavior: insufficient_context
    evidence:
      - retrieval_latency_ms
      - retrieval_empty_total
  llm_provider:
    criticality: required_for_generated_answer
    owner: ai-platform
    failure_behavior: temporary_unavailable
    evidence:
      - provider_http_status
      - model_latency_ms
      - fallback_total
  calendar_tool:
    criticality: optional
    owner: workplace-integrations
    failure_behavior: omit_live_calendar_detail
    evidence:
      - tool_error_total
      - tool_fallback_total

unsafe_to_degrade:
  - fabricate_policy_source
  - bypass_authorization
  - execute_travel_booking_without_confirmation
```

這份檔案有幾個容易被忽略的好處。

- `user_job` 避免團隊把「回傳一段文字」當成完成。
- `response_deadline_ms` 讓 timeout 有對照的使用者等待上限，而不是只看 SDK 預設值。
- `criticality` 區分必要與可選依賴，避免每個 upstream error 都升成同一級事故。
- `failure_behavior` 迫使團隊選擇誠實拒答、暫時不可用、局部降級或人工處理；空白就是尚未做決定。
- `unsafe_to_degrade` 把不能用 fallback 掩蓋的情況寫清楚。安全問題通常不適合用「先回 200」處理。

有了這類文件，code review 可以問得更具體：這次新增的 tool 是必要依賴嗎？它逾時會不會卡住整個 `/ask`？產品是否接受少一段即時行事曆資訊？答案若只是「應該沒事」，代表 contract 還沒完成。

### contract 不等於 SLA

這裡的 `response_deadline_ms: 5000` 是設計目標與討論起點，不是對外 SLA，更不是已量測的 SLO。要把它升級成 SLO，至少還需要：明確的成功事件、時間窗、分母、資料來源、錯誤預算處置方式，以及對例外流量的處理。

同樣地，`failure_behavior: insufficient_context` 只是回應策略。它是否真的保護使用者，仍要由 golden dataset、抽樣 review 與安全測試驗證。Day 8 已經把 technical、quality、safety 分開；在 Day 9 寫 contract 時，也別把字串看起來合理當成已通過品質證明。

## ⑪ 降級不是「回 200」，而是維持一個誠實的較小承諾

依賴失敗時，最危險的錯誤常不是明確失敗，而是回傳看起來正常、內容卻已失真的成功。對使用者來說，這種結果很難偵測，也難以追溯。

以差旅問答為例，可以把降級決策寫成表格：

| 情境 | 可以做的降級 | 不應做的降級 | 使用者可見結果 |
| --- | --- | --- | --- |
| Retriever 暫時無回應 | 告知暫時無法取得政策，提供稍後重試 | 用模型記憶補一段未附來源的規則 | 明確的暫時失敗或資料不足 |
| Retriever 找不到來源 | 回 `insufficient_context`，請使用者補充問題 | 把空結果當作「沒有規定」 | 誠實說明沒有足夠依據 |
| LLM provider 429 | 有上限地重試、排隊或切換已驗證的備援模型 | 無限重試，讓佇列與成本一起失控 | 暫時忙碌，附可重試提示 |
| 行事曆 tool 失敗 | 省略即時行事曆資訊，保留靜態政策答案 | 猜測可用時段、假裝已建立預約 | 明示少了即時資訊 |
| 授權檢查失敗 | 拒絕存取並記錄安全事件 | 先回文件內容，稍後再補檢查 | 受控拒絕 |

「只少一個功能」不一定就是低風險。若被省略的是文件權限、來源版本或付款確認，降級可能改變整個結果的可信度。這也是為什麼 dependency map 需要標註資料類型與安全邊界，而不是只列 HTTP endpoint。

### fallback 要有停止條件

retry、cache 與備援模型都是工具，不是自動加分。每一項都要寫出停止條件，否則系統只是把單一失敗擴散成 resource exhaustion。

```text
單次 request 的總 deadline：5 秒
Retriever 最多等待：800 ms
LLM 第一次嘗試：最多 2,500 ms
只有明確可重試的錯誤才重試一次
重試前仍須保留至少 1,000 ms 給 response 與 validator
剩餘時間不足：停止嘗試，回傳受控結果
```

這不是唯一正確的數字。不同工作有不同等待容忍度；付款、病歷、批次報表和聊天問答的選擇不會一樣。重點是總 deadline 必須存在，並且每一段的 timeout 都不能偷偷超過它。

AWS 對 retry 的建議同樣提醒：重試會放大負載，且應搭配 timeout、backoff、jitter 與限制機制，而不是把「再試一次」當成預設答案。[AWS Builders’ Library：Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)

## ⑫ 一筆 request，要讓不同觀測資料說同一件事

Day 2 到 Day 8 已經分別引入 metrics、logs、traces 與 AI evaluation。Service boundary 的實務價值，在於替它們放入相同的 request context。否則 Grafana 顯示 provider error 上升，Loki 找到 parser exception，LangSmith 或 Langfuse 看見品質失敗，卻無法確認它們是否屬於同一次使用者工作。

讀者可以在自己的服務定義一個最小欄位集合：

```text
request_id             每一個外部 request 的關聯鍵
trace_id               跨 service 與 dependency 的追蹤鍵
service_name           產生事件的服務名稱
service_version        部署後可追查的版本
workflow_name          例如 travel-policy-answer
workflow_version       prompt、retrieval、policy 組合的版本
dependency_name        policy_index、llm_provider、calendar_tool
dependency_criticality required 或 optional
outcome                answered、insufficient_context、temporary_unavailable
degraded               true 或 false
```

這些欄位不應全部塞進 Prometheus label。`request_id` 與 `trace_id` 幾乎每次都不同，會造成高 cardinality；它們適合放在 log、trace 與 audit event。metrics 應只保留有限集合，例如 `dependency_name`、`outcome` 與固定的 `workflow_version`。Day 5 的 cardinality 原則在 AI workflow 一樣有效，模型讓資料變多，並沒有讓 Prometheus 突然愛上 UUID。

一個結構化 log 可以長得像這樣：

```json
{
  "event": "dependency_result",
  "request_id": "req_8f3d",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "service_name": "travel-policy-answer",
  "service_version": "2026.09.21.2",
  "workflow_version": "policy-rag-v3",
  "dependency_name": "llm_provider",
  "dependency_criticality": "required_for_generated_answer",
  "outcome": "rate_limited",
  "degraded": true,
  "retry_count": 1
}
```

不要記錄原始 prompt、授權 token、完整內部文件或未遮罩的個資，只為了「方便除錯」。把可關聯性做好，不代表取消資料最小化。需要保存輸入輸出供品質調查時，也應先由資料治理規則決定遮罩、存取控制、retention 與抽樣方式。

### 從告警回到使用者影響的調查順序

當 `llm_provider` 的 429 升高，第一個問題不該是「供應商是不是壞了」，而是「哪個使用者工作被影響、影響多少、系統是否按照 contract 降級」。可以按下面順序調查：

1. 在 metric 看 `dependency_name="llm_provider"` 的錯誤率、延遲與 fallback rate 是否同時異常。
2. 用 deployment 與 workflow version 切分，排除剛發布的 prompt 或路由變更造成的局部問題。
3. 由 exemplar 或相關 trace 找到代表性 `trace_id`，確認 retry 是否有上限、剩餘 deadline 是否足夠。
4. 在 log 以 `trace_id` 或 `request_id` 確認回應 `outcome`，看使用者得到的是受控暫時失敗、備援答案，還是裸露 exception。
5. 抽樣檢視受影響 request 的 quality 與 safety 狀態。HTTP 200 的 fallback 也需要被檢查。

這套順序不能直接證明 root cause。它的作用是把 investigation 從「所有 dashboard 都看一下」縮小到可驗證的假設。Day 10 會以 Fault、Error、Failure 把這些證據再分層：429 是 error 訊號；使用者是否未完成工作，才決定 failure 是否發生。

## ⑬ DIY：用一張 failure matrix 做桌上演練

前一個 DIY 著重畫出路徑。現在不需要啟動服務，也可以把這張圖拿來做一次桌上演練。請沿用相同的一項使用者工作，不要同時換題目；這樣你看得到 Service boundary 的設計是否前後一致。

### Step 1：選三個失敗情境

至少選一個必要 dependency、一次可選 dependency、一次安全或權限檢查。例如：

```text
A. policy_index timeout
B. calendar_tool 500
C. authorization service 回傳未知結果
```

不要只挑「最容易降級」的情境。被忽略的驗證服務往往比一個可選 widget 更接近真正的風險邊界。

### Step 2：填上 failure matrix

建立一張表，至少包含以下欄位：

| 情境 | 對外承諾是否仍能完成 | 回應策略 | 需要留下的證據 | 是否可自動重試 | 升級條件 |
| --- | --- | --- | --- | --- | --- |
| policy_index timeout | 否，無法確認政策 | `temporary_unavailable` | trace、dependency latency、request outcome | 有上限 | timeout rate 超出門檻且影響使用者 |
| calendar_tool 500 | 可，若靜態政策仍可回答 | 省略即時資訊 | tool error、degraded flag | 視 idempotency 而定 | fallback rate 持續上升 |
| authorization unknown | 否，不能確認權限 | 拒絕存取 | audit event、auth error | 通常不對同一 request 重試 | 安全事件或大量拒絕 |

表中的內容是範例。你的工作若涉及寫入、金流、醫療或內部資料，應把「可否重試」與「能否使用 cache」的判斷調得更保守。

### Step 3：安排一條人能讀懂的回應

使用者不需要知道 `vector-db deadline exceeded`，但需要知道接下來能做什麼。請替每個情境寫一段對外訊息，並避免兩種錯誤：假裝完成，或把內部細節直接丟給使用者。

```text
不佳：Internal error: upstream retriever timed out.
不佳：目前沒有相關政策。（實際上是查詢失敗）
較佳：目前無法確認最新政策內容，請稍後再試；此問題不影響既有申請資料。
```

最後一句只有在你真的知道「不影響既有申請資料」時才能寫。若不知道，不能為了讓訊息看起來安心而替系統保證。

### Step 4：用反例挑戰設計

對每一列問四個問題：

1. HTTP 200 時，使用者仍可能被誤導嗎？
2. retry 發生十次時，會不會吃掉其他 request 的資源？
3. cache 裡的資料有版本、權限與有效期限嗎？
4. 這個動作是否需要人工確認，卻被 fallback 悄悄略過？

如果有任一題答不出來，請在 matrix 留下 `UNKNOWN`，而不是把推測寫成設計保證。這張未完成的表本身，就是下一輪設計與測試的待辦清單。

### Step 5：把 Day 8 的三個狀態帶回來

每個演練情境都標一組 technical、quality、safety 結果。範例如下：

```text
policy_index timeout
technical_status = DEGRADED
quality_status = UNKNOWN
safety_status = PASS

authorization unknown
technical_status = DEGRADED
quality_status = NOT_APPLICABLE
safety_status = BLOCKED
```

`BLOCKED` 不代表服務成功；它代表系統沒有在權限未知時 fail open。`UNKNOWN` 也不是失敗率為零，它只是誠實保留了尚未能評估品質的狀態。

讀者完成演練後，應能用同一張 matrix 說清楚：哪個事件需要 pager，哪個事件只需建立 ticket，哪個事件要送入 quality review，哪個事件屬於安全告警。這些決策應由服務契約與風險決定，不能只看某個 HTTP status。

## ⑭ 常見的邊界誤判

### 「供應商 SLA 很高，所以我們的 Service 不需要設計 fallback」

外部服務的可用性承諾不會自動變成你的使用者體驗。網路、DNS、quota、帳號設定、整合程式與你自己的 deadline 都在邊界裡。你可以沒有 fallback，但仍要明確定義失敗回應、觀測方式與使用者溝通。

### 「有 cache 就算有降級」

cache 只有在資料版本、權限、TTL 與使用情境都被驗證時才是降級方案。對於最新政策、付款狀態或授權資訊，陳舊資料可能比明確拒答更有害。把 cache hit rate 當成可靠性證明也同樣危險。

### 「每個 dependency error 都要 page」

這會把 pager 變成依賴健康檢查的轉發器。必要依賴的錯誤若已由 retry 吸收、使用者工作未受影響，可能適合 ticket 或容量追蹤；可選依賴的錯誤則更可能只需觀察。反過來說，少量 authorization failure 也可能需要立即處理。告警門檻要回到 impact，而不是元件的音量。

### 「模型回答有文字，就表示 Service 完成」

Day 8 已說明生成結果還有 quality 與 safety 軸。回答若沒有來源、引用不相符、繞過 tool policy，或在資料不足時過度自信，都可能是使用者工作的 failure，即使 API 正常回 200。

## ⑮ 本文的概念驗收清單

這裡是讀者可自行完成的設計檢查。本文沒有建立 `Day9/DIY`、安裝依賴、啟動服務或執行以下檢查，因此不宣稱任何程式或架構已驗證。

- [ ] 選出一項使用者可辨識的能力，並用一句話寫出它的 Service contract。
- [ ] 從 client 到 response 畫出一條 critical path，而不只畫 deployment 元件。
- [ ] 列出每個必要與可選依賴，包含 owner、失敗時的預期行為與可觀測訊號。
- [ ] 對 AI workflow 分開標示 retriever、model、tool、validator 與 policy 的責任邊界。
- [ ] 對至少一個 dependency failure 寫下 retry、fallback、拒絕或人工 review 的選擇與理由。
- [ ] 確認 monitoring、deployment、authorization 等 control plane 能力是否也在 failure model 裡。
- [ ] 把觀測到、但尚未能代表使用者結果的訊號標成 `UNKNOWN`，不把它直接當 SLI。

## ⑯ 本文結論

Service 是一項對外能力連同它的依賴與失敗行為。傳統系統的 API、DB 與外部服務如此；AI workflow 裡的 Retriever、LLM provider、Tool Executor、Validator 也一樣。

先畫出使用者的 critical path，再替每個依賴寫下失敗時的預期行為。下一次 timeout、錯誤答案或被阻擋的 action 出現時，這些邊界能幫助團隊判斷問題落在哪裡、接下來該問什麼。

## Day 10 預告

有了 Service 與 dependency 的邊界，下一步才能分清楚一個經常混用的因果鏈：程式裡的 bug、系統內的錯誤狀態，和使用者真正看見的失敗，並不是同一件事。Day 10 會用 `Fault → Error → Failure` 把它們拆開。

## 延伸閱讀

- [Google SRE Book：Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Book：Developing Software for Complex Machines](https://sre.google/sre-book/software-engineering-in-sre/)
- [Google SRE Book：Postmortem Culture](https://sre.google/sre-book/postmortem-culture/)
- [AWS：2021 年 12 月 us-east-1 事件報告](https://aws.amazon.com/message/12721/)
- [GitHub 事故報告（Incident History）](https://www.githubstatus.com/history)
