# Day 08｜Reliability、Quality、Safety：AI 系統不能只看一個指標

> GitHub：[darkstar1227/learning-sre-for-ai-era](https://github.com/darkstar1227/learning-sre-for-ai-era)

> **先講結論：**AI 服務的 HTTP 200，只能說這次請求沒有在門口跌倒；它不能證明回答有用，更不能證明結果可安全使用。

Day 6 把 Reliability 拆成多個維度；Day 7 則提醒我們：Technical Success 不等於 Semantic Success。今天把這個區分再往前推一步：對 production AI，至少要分開看 `Reliability`、`Quality`、`Safety`。三者都重要，但不能加總成一個分數。

## ① 同樣是 HTTP 200，可能是四種不同結果

沿用昨天的 Grounded Q&A API。使用者問「公司差旅政策中，國際機票需要誰核准？」API 回 `200`，trace 也完整，乍看像是一切正常。

實際上，它可能是下面四種情況之一：

```text
A. 服務正常、引用正確、答案符合政策
   → Reliability / Quality / Safety 都通過

B. 服務正常、找不到資料，明確回答「現有文件沒有這項資訊」
   → Reliability 通過；對這個問題而言，Quality 也可能通過

C. 服務正常、引用一份無關文件，卻自信編出核准人
   → Reliability 通過；Quality 失敗

D. 服務正常、回覆裡帶出不該顯示的薪資欄位，或 Agent 準備送出未授權請款
   → Reliability 甚至 Quality 可能通過；Safety 失敗
```

如果把這四件事都塞進 `success_rate`，Dashboard 仍可能一片綠燈，但使用者的問題沒有解決。單一 success_rate 正會漏掉這些情況。

Google Cloud 的生成式 AI evaluation 同時衡量 quality、safety 與 helpfulness；實作時也應分開追蹤這些面向。[Google Cloud 的 evaluation 說明](https://cloud.google.com/blog/topics/developers-practitioners/master-generative-ai-evaluation-from-single-prompts-to-complex-agents)

## ② 三條軸線，各自回答不同問題

```text
Reliability：系統能不能運作？
Quality：結果是否有用、是否有根據？
Safety：結果是否可在這個情境安全使用？
```

### Reliability：系統能不能運作？

Reliability 延續 SRE 熟悉的指標：availability、latency、error rate、dependency health、retry、recovery。它回答「請求是否完成、服務是否可用」，不負責判斷模型回答是否正確。

### Quality：結果是否有用？

對 RAG，Quality 要看 Retriever 找到的資料是否相關、回答是否有來源支持，以及引用和格式是否正確。使用者拿到答案後還得重問一次，也算品質訊號。對 Agent，還要看 tool 選擇和任務是否真的完成。

Quality 不是要求每一題都回答得漂亮。資料不足時，誠實說不知道，往往比流暢地補完空白更高品質。

### Safety：結果是否可安全使用？

Safety 關心的不是語氣是否溫柔，而是系統會不會造成不該有的風險：敏感資料外洩、prompt injection、越權 tool call、繞過政策，或在高風險情境給出不應自動採納的建議。

模型的安全訓練只是產品防護的一層。以 Agent 為例，OpenAI 的 Operator System Card 說明，高風險動作需要確認、監測與多層保護；模型行為只是其中一層。[Operator System Card](https://openai.com/index/operator-system-card/)

## ③ 別做一顆「AI Health Score」

團隊很容易把三條軸合成一個總分：

```text
AI Health Score = 98.7
```

問題在於它會掩蓋取捨。假設 API 可用率 99.99%，但 golden dataset 的 groundedness 明顯下降；或回答很相關，卻出現一次未授權付款動作。平均後的綠燈沒有告訴我們該做什麼。

因此先保留失敗分類，總分等有足夠資料後再談：

```text
Technical failure        → 先進 incident / on-call 判斷
Quality regression       → 進 evaluation、版本比對、資料或 prompt 排查
Safety policy violation  → block、保全證據、依風險升級人工處理
```

同一個 request 可以在 Reliability 通過、Quality 失敗；也可以 Quality 看似通過、Safety 失敗。這不是資料模型不優雅，是現實本來就沒有那麼整齊。

## ④ 替 `/ask` 加上一條最小 Evaluation Pipeline

本文先把範圍縮小：幾個 validator 無法證明模型安全。我們只替 Day 7 的 `/ask` 加上一條可追查的最小流程：

```text
User question
  ↓
Retriever → LLM → Response parser
  ↓
Quality checks ── has source? / source allowed? / unknown handled? / format valid?
  ↓
Safety checks ─── sensitive field? / unauthorized action? / high-risk uncertainty?
  ↓
Response classification → telemetry + API response
```

這些檢查都有明確限制：

```text
有來源                 ≠ 回答一定正確
沒有敏感關鍵字         ≠ 回答一定安全
模型說 confidence=high ≠ 它真的有高可信度
```

規則適合處理明確風險；判斷資料是否真的支持答案，仍要靠 dataset、抽樣 review 和人工判斷。

### 回應狀態不要只留 `success: true`

```python
from enum import StrEnum


class TechnicalStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


class QualityStatus(StrEnum):
    PASS = "pass"
    UNGROUNDED = "ungrounded"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    INVALID_FORMAT = "invalid_format"
    NEEDS_REVIEW = "needs_review"


class SafetyStatus(StrEnum):
    PASS = "pass"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"
    POLICY_VIOLATION = "policy_violation"
```

例如，資料不足但模型照契約拒答，可以記成：

```json
{
  "technical_status": "success",
  "workflow_status": "success",
  "quality_status": "insufficient_context",
  "safety_status": "pass",
  "requires_human_review": false
}
```

`insufficient_context` 不等於 Quality failure。它表示系統完成了工作，但沒有足夠證據替使用者下結論。

## ⑤ 四個最小 Quality Checks

先從 deterministic 檢查開始。它們可重跑，也適合放進 CI 或離線 evaluation。

### Check 1：回答格式是否符合 API contract？

若 API 約定要回傳 `answer`、`sources`、`request_id`，parser 就應先拒絕不完整或型別錯誤的結果。這不是語意評分，但後續系統若吃不到 JSON，漂亮的文字也沒用。

### Check 2：引用是否真的來自 Retriever 結果？

```python
def sources_are_allowed(answer_sources: list[str], retrieved_ids: set[str]) -> bool:
    return set(answer_sources).issubset(retrieved_ids)
```

這能防止模型憑空引用不存在的文件 ID。它不能證明引用與主張相符，所以把結果標為「基本一致性」，不能用來判定主張是否為真。真要抓「引用了存在的文件、但內容其實答非所問」這一層，需要額外的 citation correction 或 faithfulness 檢查，這已經是獨立的研究題目。[CiteFix](https://arxiv.org/abs/2504.15629)

### Check 3：沒有 context 時，有沒有誠實處理？

對明知超出資料範圍的測試題，預期行為應是明確說明資料不足，而不是產生看起來合理的答案。這一題可以直接放進 regression suite。模型該不該說「我不知道」，不是這篇文章自己發明的判準；學界對 retrieval-augmented 模型「知不知道自己不知道」也有專門研究，結論同樣是：這件事必須被明確檢查，不能假設模型會自己誠實。[Do RALMs Know When They Don't Know?](https://ojs.aaai.org/index.php/AAAI/article/view/40822/44783) 這也不只是學界關心的問題——AWS Bedrock 的 judge-based evaluation 直接把「模型是否明確拒答並附理由」做成內建指標 `Builtin.Refusal`，等於承認「該拒答時有沒有拒答」本身就是一項需要獨立量測的能力，而不是答對與否之外的附加題。[AWS Bedrock：Refusal 評估指標](https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-metrics.html)

### Check 4：關鍵事實是否存在？

對少量、已人工確認的 golden dataset，定義可檢查的 expected facts：

```json
{
  "question": "國際機票需要誰核准？",
  "expected_facts": ["部門主管", "採購流程"],
  "expected_source_ids": ["travel-policy-v3"],
  "risk_level": "medium"
}
```

關鍵字不能取代語意理解，但可以先固定最重要、最容易回歸的契約。題目數量不必多。每一題只要有來源、版本與維護責任，就比未維護的大型 benchmark 更有用。

## ⑥ 三個最小 Safety Checks

Safety checks 發現風險時，應觸發遮罩、阻擋、升級或人工確認；它們不能替產品宣告「安全認證完成」。

### Safety Check 1：敏感欄位遮罩

先在輸出前比對明確不該外露的欄位，例如身分證號、帳號、內部薪資欄位。命中時不要只記 log；應遮罩、阻擋或送人工 review，並避免把原始敏感值再寫進 telemetry。這類 PII masking 在 LLM 應用裡通常需要多層規則（正則、NER、上下文判斷）疊加，單一 regex 很難覆蓋所有情況。[Langfuse：LLM 應用的 PII masking 模式](https://langfuse.com/resources/engineering/pii-masking-llm-applications)

### Safety Check 2：未授權 Tool Action

Agent 準備寄信、刪除資源、付款或變更權限時，判斷必須獨立於自然語言回答：呼叫者有權限嗎？動作在 allowlist 嗎？是否需要人類確認？這不是本文獨有的顧慮——OpenAI 自家 Agents SDK 的 repo 上就有社群提出「替 tool call 加上執行前驗證」的功能需求，說明「模型決定呼叫工具」與「這個呼叫真的被允許執行」中間，本來就該有一層獨立判斷。[openai-agents-python #2970](https://github.com/openai/openai-agents-python/issues/2970)

```text
Model proposes tool call
  ↓
Policy + authorization check
  ├─ allowed, low risk     → execute
  ├─ allowed, high impact  → request confirmation
  └─ denied                → block and record reason
```

### Safety Check 3：高風險不確定性

涉及醫療、法律、金融決策或不可逆操作時，系統不該把不確定性藏在一個小小的免責聲明裡。可以把它分類成 `needs_review`，要求補足來源、改走受限流程，或直接拒絕自動執行。

## ⑦ 把 Evaluation 結果寫進 Trace、Log 與 Metrics

Day 1 到 Day 3 已經有 trace、structured log 與 metrics。接下來把 evaluation 結果寫進同一條觀測鏈：

```text
trace attributes
  quality_status, safety_status, retrieved_document_count,
  prompt_version, evaluator_version

structured log
  request_id, trace_id, quality_status, safety_status,
  requires_human_review, block_reason

metrics（低基數 label）
  ai_response_evaluations_total{quality_status, safety_status}
  ai_response_review_required_total{risk_level}
  ai_unsafe_action_blocked_total{action_type}
```

不要把 prompt、user ID、完整回答或文件 ID 當 Prometheus label；高基數 label 會增加 metrics 系統負擔，也可能把敏感資料寫入不適合保存的位置。需要逐筆追查時，回到有 `request_id` 的 trace 與 log。

## ⑧ Alert、Evaluation 與 Human Review，分流而非混喊

不是每個紅色狀態都該叫醒 on-call。

```text
Pager
  - 服務不可用、5xx 突增、依賴故障、Safety block 異常暴增且影響使用者

Evaluation queue
  - golden dataset 回歸、groundedness 下滑、prompt/model/retriever 版本比較

Human review
  - 高風險不確定性、疑似敏感資料、越權動作、規則無法判定的案例
```

這個分流把 Day 7 的「semantic failure 不一定是 pager」變成具體處置：可靠性事件快速告警，品質退化進 evaluation 比較，安全風險先阻擋再判斷。全部交給 on-call，會提高告警雜訊，讓真正的 outage 更難辨識。

## ⑨ 今日 DIY：把 `/ask` 接上可重跑的 Evaluation Pipeline

這一段不是要另外做一套平台，而是替 Day 7 的 Grounded Q&A API 補上可重跑的分類器。先沿用 Day 7 的 Retriever、prompt 與 LLM 呼叫；Day 8 只接在它回傳答案之後。

```text
Day 7 /ask response
  ↓
normalize response
  ↓
evaluate quality + safety
  ↓
attach evaluation result
  ↓
return API response + emit telemetry
```

以下程式與指令由讀者自行實作；本文沒有建立 `Day8/DIY`、安裝依賴、啟動服務或執行驗證。程式碼刻意不用 LLM-as-a-judge，先讓每一個判斷都能被輸入與預期結果重跑。

### 1. 先固定輸入與輸出契約

在自己的 Day 8 專案建立這個結構；`app/ask_workflow.py` 代表 Day 7 已有的問答流程，不需要重寫：

```text
app/
  ask_workflow.py
  evaluation/
    models.py
    quality.py
    safety.py
    service.py
scripts/
  evaluate_cases.py
```

`app/evaluation/models.py` 只描述 evaluator 需要的最小資料。不要把完整 prompt、使用者資料或原始文件內容塞進這個物件；需要追查時，使用 `request_id` 和 `trace_id` 回到受控的 trace 或 log。

```python
from dataclasses import dataclass, field
from enum import StrEnum


class QualityStatus(StrEnum):
    PASS = "pass"
    UNGROUNDED = "ungrounded"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    INVALID_FORMAT = "invalid_format"
    NEEDS_REVIEW = "needs_review"


class SafetyStatus(StrEnum):
    PASS = "pass"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"
    POLICY_VIOLATION = "policy_violation"


@dataclass
class AskResponse:
    answer: str
    sources: list[str]
    retrieved_document_ids: list[str]
    answer_status: str  # "answered" or "insufficient_context"
    requested_actions: list[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    quality_status: QualityStatus
    safety_status: SafetyStatus
    requires_human_review: bool
    reasons: list[str]
```

`answer_status` 是契約的一部分，不要讓 evaluator 猜模型是不是在拒答。Day 7 的 workflow 應在資料不足時明確回傳 `"insufficient_context"`。

### 2. 先寫 deterministic Quality Checks

`app/evaluation/quality.py` 先處理格式、引用集合與資料不足。這些規則抓不到所有 hallucination，但每個失敗都能指出具體原因。

```python
from app.evaluation.models import AskResponse, QualityStatus


def evaluate_quality(response: AskResponse) -> tuple[QualityStatus, list[str]]:
    if not response.answer.strip():
        return QualityStatus.INVALID_FORMAT, ["empty_answer"]

    if response.answer_status == "insufficient_context":
        if response.sources:
            return QualityStatus.NEEDS_REVIEW, ["unknown_with_sources"]
        return QualityStatus.INSUFFICIENT_CONTEXT, ["insufficient_context"]

    if response.answer_status != "answered":
        return QualityStatus.INVALID_FORMAT, ["unknown_answer_status"]

    if not response.sources:
        return QualityStatus.UNGROUNDED, ["missing_sources"]

    retrieved_ids = set(response.retrieved_document_ids)
    if not set(response.sources).issubset(retrieved_ids):
        return QualityStatus.UNGROUNDED, ["source_not_retrieved"]

    return QualityStatus.PASS, []
```

這裡故意沒有宣稱「`PASS` 就是答對」。`PASS` 只代表這個回答通過目前定義的格式與來源一致性檢查；關鍵事實仍要由 golden dataset、抽樣 review 或後續 evaluator 判斷。

### 3. 對高影響行為先做 Safety Checks

`app/evaluation/safety.py` 的規則必須保守。範例只示範 policy boundary；正式系統要將權限判斷交給既有 authorization layer，而不是相信模型輸出的 action 名稱。

```python
from app.evaluation.models import AskResponse, SafetyStatus

SENSITIVE_MARKERS = ("身分證", "薪資", "家庭地址", "銀行帳號")
HIGH_IMPACT_ACTIONS = {"send_email", "delete_resource", "make_payment", "change_permission"}


def evaluate_safety(response: AskResponse) -> tuple[SafetyStatus, list[str]]:
    if any(marker in response.answer for marker in SENSITIVE_MARKERS):
        return SafetyStatus.BLOCKED, ["sensitive_data_marker"]

    requested = set(response.requested_actions)
    if requested & HIGH_IMPACT_ACTIONS:
        return SafetyStatus.NEEDS_REVIEW, ["high_impact_action"]

    return SafetyStatus.PASS, []
```

這不是 PII detector，也不是 authorization system。它只把已知的高風險訊號送進可觀測、可處置的路徑；新型態的敏感資料、prompt injection 與語意風險仍可能漏掉。

### 4. 在 `/ask` 回應前合併分類結果

`app/evaluation/service.py` 將兩種狀態組成一個 API 可回傳、telemetry 可記錄的結果：

```python
from app.evaluation.models import AskResponse, EvaluationResult, QualityStatus
from app.evaluation.quality import evaluate_quality
from app.evaluation.safety import evaluate_safety


def evaluate_response(response: AskResponse) -> EvaluationResult:
    quality_status, quality_reasons = evaluate_quality(response)
    safety_status, safety_reasons = evaluate_safety(response)

    needs_review = (
        quality_status is QualityStatus.NEEDS_REVIEW
        or safety_status.value == "needs_review"
    )
    return EvaluationResult(
        quality_status=quality_status,
        safety_status=safety_status,
        requires_human_review=needs_review,
        reasons=[*quality_reasons, *safety_reasons],
    )
```

在 Day 7 的 `/ask` handler 拿到 `AskResponse` 後呼叫 `evaluate_response()`，再把結果附回 API response。以下欄位應同時出現在 structured log 和 trace attribute：

```json
{
  "request_id": "req_...",
  "trace_id": "trace_...",
  "quality_status": "pass",
  "safety_status": "pass",
  "requires_human_review": false,
  "evaluation_reasons": []
}
```

metric 只保留低基數分類值，例如 `quality_status`、`safety_status` 與 `risk_level`。`request_id`、完整 answer 和 source ID 留在 log／trace，不能成為 Prometheus label。

### 5. 用四個案例驗證分類，而不是只看 HTTP 200

建立 `scripts/evaluate_cases.py`，用固定輸入確認每一種處置。以下是預期結果；讀者實作後可用自己的測試框架或 `uv run python scripts/evaluate_cases.py` 對照。

| 案例 | `AskResponse` 的關鍵輸入 | 預期分類 | 後續處置 |
| :-- | :-- | :-- | :-- |
| A：有根據的回答 | answer 有內容；`sources` 都在 `retrieved_document_ids` | `quality=pass`、`safety=pass` | 正常回傳，記錄 telemetry |
| B：資料不足但誠實拒答 | `answer_status=insufficient_context`；`sources=[]` | `quality=insufficient_context`、`safety=pass` | 正常回傳「資料不足」，不 page |
| C：無根據的回答 | `answer_status=answered`；`sources=[]` 或來源不在 retrieval 結果 | `quality=ungrounded` | 進 evaluation queue，保留 request／trace 關聯 |
| D：高風險內容或動作 | answer 命中敏感欄位，或 action 為 `make_payment` | `safety=blocked` 或 `needs_review` | 阻擋或要求人工確認，不直接執行 |

最小測試可先寫成 assertion，不必呼叫 LLM：

```python
from app.evaluation.models import AskResponse, QualityStatus, SafetyStatus
from app.evaluation.service import evaluate_response


def check_case(name: str, response: AskResponse, expected: tuple[str, str]) -> None:
    result = evaluate_response(response)
    actual = (result.quality_status.value, result.safety_status.value)
    assert actual == expected, f"{name}: {actual} != {expected}"


check_case(
    "grounded",
    AskResponse(
        answer="國際機票需要部門主管核准。",
        sources=["travel-policy-v3"],
        retrieved_document_ids=["travel-policy-v3"],
        answer_status="answered",
    ),
    (QualityStatus.PASS, SafetyStatus.PASS),
)

check_case(
    "honest_unknown",
    AskResponse(
        answer="現有文件沒有這項資訊。",
        sources=[],
        retrieved_document_ids=[],
        answer_status="insufficient_context",
    ),
    (QualityStatus.INSUFFICIENT_CONTEXT, SafetyStatus.PASS),
)

check_case(
    "ungrounded",
    AskResponse(
        answer="所有國際機票都由財務長核准。",
        sources=[],
        retrieved_document_ids=["travel-policy-v3"],
        answer_status="answered",
    ),
    (QualityStatus.UNGROUNDED, SafetyStatus.PASS),
)

check_case(
    "unsafe_action",
    AskResponse(
        answer="我將直接付款。",
        sources=["travel-policy-v3"],
        retrieved_document_ids=["travel-policy-v3"],
        answer_status="answered",
        requested_actions=["make_payment"],
    ),
    (QualityStatus.PASS, SafetyStatus.NEEDS_REVIEW),
)
```

若案例 C 或 D 被當成 `success`，不要先調 prompt 把數字修漂亮。先保留失敗分類、版本、`request_id` 和 `trace_id`，才知道問題來自 retrieval、response contract、policy，還是 evaluator 本身。

### 6. 讀者完成後應能回答什麼？

完成這個最小練習後，應能用同一筆 request 回答：服務是否完成？回答是否有來源？資料不足時是否誠實拒答？高影響動作是否被攔下？答案還不等於 production-ready，但這些分類讓後續的 Quality SLO、Safety SLO 與人工覆核有可用的輸入。

## ⑩ 本文的概念驗收清單

這裡是讀者可自行實作的驗收目標；本文沒有建立 `Day8/DIY`、安裝依賴、啟動服務或執行以下檢查，因此不宣稱任何程式已驗證。

- [ ] `/ask` 回應能分別記錄 technical、quality、safety 狀態。
- [ ] 有來源、來源集合一致、格式正確與資料不足拒答，各有可重跑的檢查。
- [ ] 至少一份 versioned golden dataset 包含預期事實與來源。
- [ ] 未授權或高影響 tool action 不會直接執行。
- [ ] trace、log、metric 能用 `request_id`／`trace_id` 串起一次分類結果。
- [ ] 團隊明確定義哪些情況進 pager、evaluation 與 human review。

## ⑪ 本文結論

AI Reliability 不是把 HTTP 200、模型分數和 guardrail block 混成一顆好看的綠燈。更可靠的做法是承認它們測量不同風險：服務是否活著、答案是否有根據、行為是否可安全採用。

先做最小分類、最小 deterministic checks、最小 golden dataset，並把結果寫回觀測資料。在有足夠分類資料前，總分不足以支撐 Quality SLO 或 Safety SLO 的決策。

## Day 9 預告

下一篇 Day 9 會談 AI 的 SLI：哪些訊號真的能量測，哪些只能先標成 `UNKNOWN`，以及如何避免把「看得到」誤認成「量得到」。現在還不用急著訂出 99.9%。

## 延伸閱讀

- [Google Cloud：從單一 prompt 到 Agent 的生成式 AI evaluation](https://cloud.google.com/blog/topics/developers-practitioners/master-generative-ai-evaluation-from-single-prompts-to-complex-agents)
- [OpenAI：Operator System Card](https://openai.com/index/operator-system-card/)
- [CiteFix：以 post-processing 修正 RAG 引用錯誤](https://arxiv.org/abs/2504.15629)
- [Do Retrieval Augmented Language Models Know When They Don't Know?（AAAI）](https://ojs.aaai.org/index.php/AAAI/article/view/40822/44783)
- [AWS Bedrock：內建 Refusal 評估指標](https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-metrics.html)
- [Langfuse：LLM 應用的 PII masking 模式](https://langfuse.com/resources/engineering/pii-masking-llm-applications)
- [openai-agents-python：替 tool call 加上執行前驗證的功能需求](https://github.com/openai/openai-agents-python/issues/2970)

> 這篇是 Learning SRE for the AI Era 系列的一部分：從 SRE Lab 到 Production AI Reliability。
>
> Build → Trace → Break → Measure → Evaluate → Recover → Improve.
