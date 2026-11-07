# Day 07｜Technical Success ≠ Semantic Success：AI 系統如何「正常地失敗」？

> GitHub：[darkstar1227/learning-sre-for-ai-era](https://github.com/darkstar1227/learning-sre-for-ai-era)

> **結論先說：HTTP 200、模型回覆完成、trace 全綠，都只能證明技術流程跑完；它們不能證明使用者拿到可用、正確而且安全的答案。**

Day 6 把 Reliability 拆成多個維度。今天補上 AI 系統最容易漏看的那一層：**語意可靠性（semantic reliability）**。傳統服務常問「請求成功了嗎？」；LLM 應用還必須問「這個回答讓使用者把事情做對了嗎？」。

## 兩個 API 都回傳 HTTP 200，事情卻不一樣

假設同事詢問：

> 公司的遠端工作規範是什麼？

系統 A 回 `HTTP 500`。監控會響、error rate 會上升，值班的人很快就知道出事了。

系統 B 回 `HTTP 200`，延遲正常、LLM 呼叫也成功，卻回答「所有員工每週可遠端三天」。實際規範是每週最多兩天，還要主管核准。

| 面向             | 系統 A            | 系統 B           |
| ---------------- | ----------------- | ---------------- |
| HTTP status      | 500               | 200              |
| 傳統監控         | 通常會告警        | 可能一片正常     |
| 使用者拿到的結果 | 沒有答案          | 錯誤答案         |
| 失敗類型         | Technical failure | Semantic failure |

第二種情況比較麻煩：系統「正常」地把人帶到錯的地方。若只看可用率，甚至可以得到漂亮但誤導的數字。

## 不只一種 Success

對 LLM workflow 而言，至少要把成功拆開看：

| 層次                   | 要問的問題                     | 例子                                    |
| ---------------------- | ------------------------------ | --------------------------------------- |
| Infrastructure success | 基礎設施是否可用？             | Pod、資料庫、網路都正常                 |
| Technical success      | 請求是否依預期完成？           | API 回 200、parser 沒拋例外             |
| Workflow success       | 各步驟是否照流程完成？         | 有取回文件、組好 prompt、拿到可解析輸出 |
| Semantic success       | 回答是否正確、相關、遵守限制？ | 答案有依據，且沒有捏造規範              |
| Task success           | 使用者是否真的完成任務？       | 同事依答案送出正確申請                  |

這不是要把每次對話都變成哲學辯論。目的是讓我們不要把不同問題塞進同一個「success」欄位。技術成功是語意成功的必要條件，但不是充分條件。

## Technical failure 與 semantic failure

### Technical failure：流程沒跑完

Timeout、資料庫無法連線、模型供應商失敗、rate limit、tool 呼叫出錯、JSON parser 例外，都屬於這一類。Metrics、logs、traces、health check 與 alert 很擅長抓它們；這正是前幾天 SRE 基本功派上用場的地方。

### Semantic failure：流程跑完，但結果不可靠

常見情況包括：

- 回答和來源文件矛盾。
- 找不到資料時，模型仍補出看似合理的內容。
- 回答沒有處理問題中的條件或時間範圍。
- 引用的文件存在，但不能支持這個結論。
- 語氣很肯定，卻沒有足夠證據。

這類問題未必是「hallucination」而已。檢索到過期文件、prompt 漏掉限制、工具回傳了錯誤欄位、評估題目沒有涵蓋例外案例，都可能讓它發生。把所有問題叫 hallucination，就像把所有 HTTP 錯誤都叫「網路壞了」：方便，但沒辦法修。

2024 年 Google 搜尋的 AI Overviews 功能是這類失敗的公開示範。它把生成式摘要直接放進搜尋結果最上方，技術上運作完全正常：request 有回應、內容格式工整、看起來像一般搜尋結果的延伸。但摘要內容本身建議在披薩上塗膠水防止起司滑動、建議吃石頭補充礦物質，這些答案後來被追蹤出源自被誤當成可信來源的諷刺文章與論壇留言。[The Verge：Google AI Overviews 報導](https://www.theverge.com/2024/5/23/24162896/google-ai-overview-search-glue-pizza-cheese) 沒有任何一個環節回傳錯誤碼，問題完全發生在「回答是否可信」這一層。

## 為什麼 HTTP 200 不夠？

`200` 的契約是「伺服器成功處理了這個 HTTP 請求」，不是「內容已經過事實審核」。LLM 的輸出本質上是依模型與提供的上下文產生；API 層無法從 status code 判斷某一句是否被來源支持。

這也是評估要成為可靠性工作一部分的原因。Google SRE 將 correctness 列為系統健康的重要面向；對 LLM 應用，除了 availability、latency、error rate，還需要能反映任務品質的指標與測試集。指標不是越多越好，而是要能回答「這次成功，對誰成功？」。[Google SRE：Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)

## 今日 DIY：做一個可被檢查的 Grounded Q&A API

今天的 DIY 不追求完整 RAG，也不需要先引入 embedding 或 vector database。先建立一個小且可控的問答流程：

```text
User question
  ↓
Keyword retrieval
  ↓
Known document
  ↓
Grounded prompt
  ↓
LLM
  ↓
Answer + sources + evaluation metadata
```

這裡的程式與指令是**讀者自行實作的步驟**；本文沒有執行、啟動或驗證 Day7 的 DIY。

### 1. 先把知識範圍縮小

建立 `data/company_policy.md`，只放幾條可驗證的規則：

```markdown
# Company Work Policy

## Remote Work

- Full-time employees may work remotely up to two days per week.
- Remote work requires manager approval.
- Employees must be available during core hours from 10:00 to 16:00.

## Annual Leave

- Employees receive 12 days of annual leave after completing one year.
- Leave requests should be submitted at least three business days in advance.
```

Production RAG 的文件當然更大、更亂，也更有可能過期；但第一個練習應讓「答案是否正確」有明確答案。否則你連評估失敗了，還是題目本身無法判定，都分不清。

### 2. 用最簡單的 retrieval，先看見資料流

先不追求演算法，讓 retrieval 的行為透明即可：

```python
def retrieve_context(question: str) -> list[Document]:
    q = question.lower()
    if "remote" in q:
        return [remote_work_document]
    if "leave" in q:
        return [annual_leave_document]
    return []
```

關鍵不是 keyword matching 有多聰明，而是每次回應都記下它選了哪些文件。日後換成 vector search 或 reranker 時，這份可觀測性仍然需要保留。

### 3. 把「不知道」寫進 prompt 契約

Prompt 要明說回答只能依據提供內容，資料不足時必須回答不知道，而不是靠模型「盡量幫忙」：

```text
Answer only from the supplied policy documents.
If the documents do not contain the answer, say that the information is unavailable.
For every policy claim, cite the supporting document ID.
Do not infer exceptions or invent company rules.
```

這不是保證模型永遠正確的魔法咒語；它是可測試的行為契約。之後可以用沒有相關文件的問題，測試系統是否確實拒答。

### 4. 回傳能讓人追查的 metadata

不要只回傳 `answer`。最小回應可以長這樣：

```json
{
  "answer": "Full-time employees may work remotely up to two days per week, subject to manager approval.",
  "sources": ["company-policy-remote-work"],
  "retrieved_document_ids": ["company-policy-remote-work"],
  "retrieval_count": 1,
  "answer_status": "answered",
  "prompt_version": "grounded-qa-v1",
  "technical_success": true,
  "semantic_risk": "unknown",
  "request_id": "req_..."
}
```

`semantic_risk: "unknown"` 很重要。沒有執行評估或人工覆核前，不要把 `technical_success: true` 偷換成「答案已被證明正確」。誠實的未知值比假裝精準有用。

同一筆 trace 也應至少能關聯 `request_id`、`trace_id`、模型識別、`input_tokens` 與 `output_tokens`。它們不會替你判答案對錯，卻能在發現錯答後回答更實際的問題：是哪個 prompt 版本、哪次檢索、哪個模型設定造成的？

## 把語意失敗變成可觀測事件

先為這個小 API 準備幾類測試問題：

| 類型     | 問題                         | 預期行為                        |
| -------- | ---------------------------- | ------------------------------- |
| 可回答   | 遠端工作每週最多幾天？       | 回答兩天，引用 remote-work 文件 |
| 條件題   | 遠端工作是否需要核准？       | 明確提到主管核准                |
| 不可回答 | 可以申請居家辦公設備補助嗎？ | 表示資料不足，不自行編造        |
| 反例     | 所有人都能每週遠端三天嗎？   | 否定錯誤前提，回到文件內容      |

每筆結果都可以檢查幾件事：檢索是否找對文件、回答是否被來源支持、該拒答時是否拒答、引用是否可追溯。這些判斷未來可做成離線 evaluation，也可抽樣交由人工覆核；兩者都不是從 HTTP status 自動推導出來的。

把這些案例存成 **Golden Dataset**（例如 `data/golden_dataset.json`），為每一題保留預期結論、允許的 source ID 與預期行為。每次修改 retrieval、prompt 或模型後重跑它。結果至少可分成 `Correct`、`Unsupported`、`Wrong format` 與 `Failed`；前兩種看內容，後兩種常能指向 response validator 或技術流程。這就是把「剛剛好像答錯了」變成可回歸的工程訊號。

單筆 hallucination 通常不該直接叫醒 Pager。先記錄與分類，再看失敗率、嚴重性和受影響任務；涉及安全、法律、醫療或高風險操作時，才要把升級與人工介入規則事先寫清楚。

業界對這件事已有很實際的教訓。以 2023 年的 Air Canada 案為例，聊天機器人提供了不正確的退款資訊；技術上能對話不等於公司能把錯誤答案當成免責理由。這不是在說每個 FAQ bot 都要上法庭，而是在提醒我們：使用者會把系統輸出當成行動依據。[Civil Resolution Tribunal 的裁決](https://decisions.civilresolutionbc.ca/crt/crtd/en/item/525847/index.do)

## 先把「成功」拆成可判斷的狀態

若 API 只回 `200` 或 `500`，它能回答的問題很有限：程式有沒有例外？資料庫連不連得上？它無法說明這句答案能不能拿去報帳、執行或相信。

Day 7 的目的不是做出一個能判定所有真假的超級 evaluator。那樣的承諾通常會比模型本身更不可靠。今天要做的是建立一個明確的 response contract，讓每次回答至少能被分到正確的處置路徑。

```text
transport success
    ↓
workflow success
    ↓
answer contract valid
    ↓
evidence available
    ↓
task outcome known or still unknown
```

這五層不必永遠一起成功。例如使用者詢問不在公司政策範圍內的問題，系統可以完成 HTTP request、完成 retrieval、明確回覆「文件沒有這項資訊」，而且那是一次好的結果。硬湊出一個聽起來流暢的答案，反而比較像失敗。

### 一份可用的最小分類表

先採用少量且可解釋的狀態。太早塞進二十個 label，最後通常只會得到一張沒人敢用的 dashboard。

| 層次 | 問題 | 建議欄位 | 可以自動判斷的部分 | 不能偷渡的結論 |
| --- | --- | --- | --- | --- |
| Technical | request 有沒有完成？ | `technical_status` | timeout、5xx、schema error | 答案正確 |
| Workflow | retrieval、model、parser 有沒有依序完成？ | `workflow_status` | step result、retry、fallback | 使用者完成任務 |
| Contract | 回應格式是否合約內？ | `answer_status` | enum、必填欄位、source ID 格式 | 引用內容真的支持答案 |
| Evidence | 答案是否有可追溯的依據？ | `source_status` | source 是否來自本次 retrieval | 文件內容必然正確或最新 |
| Task | 使用者是否拿到可採用的結果？ | `task_status` | 部分可由確認事件推斷 | 未量測的使用者行為 |

`task_status` 可以是 `completed`、`not_completed`、`unknown`。最後那個 `unknown` 不是偷懶，它是在提醒我們尚未收到能證明任務完成的訊號。若使用者只是看到回答就離開頁面，服務不能擅自把它記成成功。

### 兩個看似相同、實際不同的 200

案例 A：使用者問「遠端工作一週最多幾天？」系統找得到 `company-policy-remote-work`，回答兩天，並列出文件 ID。這可能是可進一步評估的 grounded answer。

案例 B：使用者問「是否有居家辦公設備補助？」系統沒有找到相關文件，卻回覆「每人每年 3,000 元」。HTTP 200、JSON schema、甚至模型延遲都可能完美；但這筆回應應被標為 `unsupported` 或 `ungrounded`，不能和案例 A 一起進「成功率」。

這個區別也影響事故處理。案例 A 的使用者回報可能是文件版本過期；案例 B 則可能是 prompt 沒有限制、retriever 沒有空結果保護，或 parser 把模型臆測包裝成事實。症狀不同，第一個排查方向也不同。

## 實作一個不會假裝全知的回應契約

以下範例沿用前面的政策問答服務。讀者可以放進自己的 Day 7 DIY 專案；本文不會建立目錄、安裝依賴、啟動 server 或替你執行它。

先定義資料模型。這裡的 enum 不是為了漂亮，而是讓 model、validator、log、trace 和測試都在講同一套語言。

```python
# app/contracts.py
from enum import StrEnum

from pydantic import BaseModel, Field


class TechnicalStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class WorkflowStatus(StrEnum):
    COMPLETED = "completed"
    DEGRADED = "degraded"
    FAILED = "failed"


class AnswerStatus(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    INVALID_FORMAT = "invalid_format"


class SourceStatus(StrEnum):
    GROUNDED = "grounded"
    NO_CONTEXT = "no_context"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class TaskStatus(StrEnum):
    COMPLETED = "completed"
    NOT_COMPLETED = "not_completed"
    UNKNOWN = "unknown"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AskResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    retrieved_document_ids: list[str] = Field(default_factory=list)
    technical_status: TechnicalStatus
    workflow_status: WorkflowStatus
    answer_status: AnswerStatus
    source_status: SourceStatus
    task_status: TaskStatus = TaskStatus.UNKNOWN
    prompt_version: str
    request_id: str
```

有兩個刻意保留的限制：第一，`task_status` 預設 `unknown`，因為 API 回傳瞬間通常還不知道使用者有沒有完成工作；第二，`source_status=grounded` 只代表引用集合通過目前檢查，不代表文件一定正確、完整或符合最新人事規章。

### 將 raw model output 與 API response 分開

不要把 LLM 的原始字串直接當 API response。模型輸出是外部輸入；即使你自己租用模型，它仍可能截斷、格式錯誤或忽略指令。

先定義一個模型希望輸出的中介格式：

```python
# app/model_output.py
from pydantic import BaseModel, Field


class CandidateAnswer(BaseModel):
    answer: str = Field(min_length=1)
    cited_document_ids: list[str] = Field(default_factory=list)
    says_insufficient_context: bool = False
```

再將它轉成對外 contract。轉換層是你放規則的地方，不該把這些判斷散落在 route、prompt 或 Grafana query 裡。

```python
# app/response_builder.py
from uuid import uuid4

from app.contracts import (
    AnswerStatus,
    AskResponse,
    SourceStatus,
    TechnicalStatus,
    WorkflowStatus,
)
from app.model_output import CandidateAnswer


def build_response(
    candidate: CandidateAnswer,
    retrieved_document_ids: list[str],
    prompt_version: str,
) -> AskResponse:
    retrieved = set(retrieved_document_ids)
    cited = set(candidate.cited_document_ids)

    if candidate.says_insufficient_context:
        return AskResponse(
            answer=candidate.answer,
            sources=[],
            retrieved_document_ids=retrieved_document_ids,
            technical_status=TechnicalStatus.SUCCESS,
            workflow_status=WorkflowStatus.COMPLETED,
            answer_status=AnswerStatus.INSUFFICIENT_CONTEXT,
            source_status=SourceStatus.NO_CONTEXT,
            prompt_version=prompt_version,
            request_id=f"req_{uuid4().hex}",
        )

    if not cited or not cited.issubset(retrieved):
        source_status = SourceStatus.UNSUPPORTED
    else:
        source_status = SourceStatus.GROUNDED

    return AskResponse(
        answer=candidate.answer,
        sources=sorted(cited),
        retrieved_document_ids=retrieved_document_ids,
        technical_status=TechnicalStatus.SUCCESS,
        workflow_status=WorkflowStatus.COMPLETED,
        answer_status=AnswerStatus.ANSWERED,
        source_status=source_status,
        prompt_version=prompt_version,
        request_id=f"req_{uuid4().hex}",
    )
```

這段程式把「引用 ID 必須出現在本次 retrieval 結果中」變成 deterministic check。它抓得到模型亂塞文件 ID，卻抓不到模型引用正確文件 ID 後扭曲內容。那不是 bug；那是這個檢查的能力邊界，後面還需要 golden dataset、人工 review 或較昂貴的 evaluator。

### 空結果不是例外，也不該觸發幻想

`retrieved_document_ids=[]` 可能是三種不同事情：問題真的不在知識庫、檢索條件太嚴，或向量資料庫故障。它們不能共用同一個結論。

建議先用 workflow event 區分：

```python
# app/retrieval_result.py
from enum import StrEnum

from pydantic import BaseModel, Field


class RetrievalOutcome(StrEnum):
    FOUND = "found"
    EMPTY = "empty"
    FAILED = "failed"


class RetrievalResult(BaseModel):
    outcome: RetrievalOutcome
    document_ids: list[str] = Field(default_factory=list)
    error_type: str | None = None
```

當 `outcome=EMPTY`，服務可以回 `insufficient_context`，技術與 workflow 仍可視為成功。當 `outcome=FAILED`，則應保留 dependency error、依既有產品策略 retry 或 degraded response；不要把它偽裝成「找不到資料」。

```text
EMPTY retrieval
  = 搜尋完成，沒有命中

FAILED retrieval
  = 搜尋沒完成，不知道是否本來會命中
```

這個差異在 incident review 非常有用。假如每天下午 `empty_retrieval_rate` 同時上升、vector DB timeout 也增加，不能先說使用者突然都問冷門問題；先檢查 dependency health 和 deployment 變更。

## 把 API route 寫成一條可觀察的流程

FastAPI 的 `response_model` 能把對外輸出限制在既定 schema，並讓 OpenAPI 顯示契約；若 route 回傳的資料違反 response model，FastAPI 會把它視為伺服器端 contract violation。這正是這裡不應跳過 response model 的原因。[FastAPI：Response Model](https://fastapi.tiangolo.com/tutorial/response-model/)

下面的 route 用同步示例保持焦點。讀者若改成 async client，仍要保留同樣的 failure boundary 與欄位，而不是只把 `def` 換成 `async def`。

```python
# app/main.py
import logging
from time import perf_counter

from fastapi import FastAPI

from app.contracts import AskRequest, AskResponse
from app.model_output import CandidateAnswer
from app.response_builder import build_response

logger = logging.getLogger("policy_qa")
app = FastAPI()


def retrieve(question: str) -> list[str]:
    if "遠端" in question:
        return ["company-policy-remote-work"]
    return []


def ask_model(question: str, document_ids: list[str]) -> CandidateAnswer:
    if not document_ids:
        return CandidateAnswer(
            answer="現有政策文件沒有這項資訊。",
            says_insufficient_context=True,
        )
    return CandidateAnswer(
        answer="全職員工每週最多可遠端工作兩天，且須經主管核准。",
        cited_document_ids=document_ids,
    )


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    started = perf_counter()
    document_ids = retrieve(payload.question)
    candidate = ask_model(payload.question, document_ids)
    response = build_response(
        candidate=candidate,
        retrieved_document_ids=document_ids,
        prompt_version="grounded-qa-v1",
    )

    logger.info(
        "ask_completed",
        extra={
            "request_id": response.request_id,
            "answer_status": response.answer_status,
            "source_status": response.source_status,
            "retrieval_count": len(document_ids),
            "latency_ms": round((perf_counter() - started) * 1000, 2),
        },
    )
    return response
```

這不是把 `source_status` 當作使用者可理解的錯誤碼。使用者需要的是清楚回答或清楚告知資料不足；`source_status` 是讓服務團隊能分析回答品質的技術訊號。把內部 enum 全丟給前端，有時只會替介面增加另一層謎語。

### 讀者可自行重跑的最小步驟

若你已在自己的 DIY 專案安裝 FastAPI 與 Uvicorn，可依專案 README 的依賴管理方式啟動範例。以下假設 entry point 是 `app.main:app`：

```bash
cd Day7/DIY
uv run uvicorn app.main:app --reload
```

另開終端機送出一筆可回答問題：

```bash
curl -sS http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question":"遠端工作每週最多幾天？"}'
```

預期 response 至少包含：

```json
{
  "answer_status": "answered",
  "source_status": "grounded",
  "retrieved_document_ids": ["company-policy-remote-work"],
  "sources": ["company-policy-remote-work"]
}
```

接著測試知識庫沒有涵蓋的問題：

```bash
curl -sS http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question":"有沒有居家辦公設備補助？"}'
```

這筆 response 應是 HTTP 200，但 `answer_status` 應為 `insufficient_context`，`sources` 應為空，`source_status` 應為 `no_context`。若它真的給出金額或福利規則，請把那筆輸入和輸出保留成 regression case，不要只把回答手動改掉就當沒發生。

本文沒有代替讀者建立 DIY、安裝套件、啟動服務或執行上述命令。預期結果描述的是可驗收條件，不是本篇已驗證的執行紀錄。

## 讓 evaluator 有證據可看，而不是只看答案文本

最小 evaluator 可以先分成兩類：contract evaluator 與 content evaluator。前者偏 deterministic，成本低且適合在線路徑；後者需要資料集、人工標註或模型 judge，適合離線或抽樣處理。

### Contract evaluator：快速抓住可證明的問題

```python
# app/evaluation.py
from app.contracts import AnswerStatus, AskResponse, SourceStatus


def evaluate_contract(response: AskResponse) -> list[str]:
    issues: list[str] = []
    retrieved = set(response.retrieved_document_ids)
    sources = set(response.sources)

    if response.answer_status is AnswerStatus.INSUFFICIENT_CONTEXT:
        if sources:
            issues.append("unknown_answer_has_sources")
        if response.source_status is not SourceStatus.NO_CONTEXT:
            issues.append("unknown_answer_wrong_source_status")
        return issues

    if response.answer_status is AnswerStatus.ANSWERED:
        if not response.answer.strip():
            issues.append("empty_answer")
        if not sources:
            issues.append("answer_has_no_sources")
        if not sources.issubset(retrieved):
            issues.append("source_not_returned_by_retrieval")
        if response.source_status is not SourceStatus.GROUNDED:
            issues.append("answered_response_not_grounded")

    return issues
```

這個 evaluator 的回傳值應是 `issues`，不是 `score=0.93`。第一天先讓工程師看得懂為什麼失敗，比先發明一個沒有校準來源的精確小數更重要。

### Content evaluator：回答是否支持預期事實

對固定政策題，可以用 golden dataset 寫下預期事實與允許來源：

```json
[
  {
    "id": "remote-work-limit",
    "question": "遠端工作每週最多幾天？",
    "expected_facts": ["兩天", "主管核准"],
    "allowed_sources": ["company-policy-remote-work"],
    "expected_answer_status": "answered"
  },
  {
    "id": "equipment-subsidy-unknown",
    "question": "有沒有居家辦公設備補助？",
    "expected_facts": [],
    "allowed_sources": [],
    "expected_answer_status": "insufficient_context"
  }
]
```

接著以固定規則驗證這個狹窄案例。注意，以下只適合確定語句的教學資料，不適合拿來宣稱能判斷所有自然語言答案。

```python
# scripts/check_golden_cases.py
from app.contracts import AnswerStatus, AskResponse


def check_case(case: dict, response: AskResponse) -> list[str]:
    failures: list[str] = []

    if response.answer_status.value != case["expected_answer_status"]:
        failures.append("unexpected_answer_status")

    if not set(response.sources).issubset(set(case["allowed_sources"])):
        failures.append("unexpected_source")

    for expected_fact in case["expected_facts"]:
        if expected_fact not in response.answer:
            failures.append(f"missing_fact:{expected_fact}")

    return failures
```

這會漏掉同義詞、否定詞和語意扭曲。例如「可遠端兩天，但無須核准」仍然包含「兩天」與「核准」。所以 golden test 通過不等於語意正確；它只是比完全不測好，並且能讓每一次 prompt 或 retrieval 變更至少經過同一組題目。

### 將失敗保留下來

一條好用的資料列不只保存問題和答案。最低限度還需要保存當時的版本與關聯 ID：

```json
{
  "dataset_case_id": "equipment-subsidy-unknown",
  "request_id": "req_4c6f...",
  "trace_id": "9a75...",
  "prompt_version": "grounded-qa-v1",
  "retrieval_index_version": "policy-2026-01",
  "model_name": "example-model",
  "answer_status": "answered",
  "source_status": "unsupported",
  "review_outcome": "incorrect"
}
```

日後有人說「新版 prompt 讓品質變差」，你才有機會比較相同 dataset、不同版本的結果。沒有版本和案例，討論很容易退化成兩個人各自挑一筆聊天紀錄，然後都說自己看見了真相。

## Metrics、logs、traces 各自記什麼

Day 2 已建立基礎觀測環境；Day 7 要開始決定 semantic signal 放在哪一層。最容易犯的錯誤，是把整段 question、answer 或 `request_id` 放進 Prometheus label。這會造成 high cardinality，讓 metrics 系統在最需要它的時候變得昂貴又難查。

| 觀測資料 | 適合記錄 | 不適合記錄 | Day 7 的用途 |
| --- | --- | --- | --- |
| Metrics | `answer_status`、`source_status`、workflow version、低基數錯誤類別 | request ID、原始問題、完整答案、文件全文 | 看趨勢與比例 |
| Structured logs | request ID、輸入摘要、validator issues、retrieved IDs | 不必要的敏感 prompt、完整機密文件 | 查單一事件 |
| Trace | step latency、model route、retry、retrieval span、關聯 ID | 未遮罩的個資、超出 retention 的內容 | 還原流程因果 |

一個可用的 Prometheus counter 可長這樣：

```python
from prometheus_client import Counter

answer_events_total = Counter(
    "answer_events_total",
    "Count policy Q&A answer outcomes.",
    ["answer_status", "source_status", "workflow_status"],
)


def record_answer_event(response: AskResponse) -> None:
    answer_events_total.labels(
        answer_status=response.answer_status,
        source_status=response.source_status,
        workflow_status=response.workflow_status,
    ).inc()
```

這些 label 的值是有限 enum，長期可控。`prompt_version` 是否要放 metric label 要看版本治理方式；如果每次實驗都產生新版本，它也可能變成高基數。保守做法是把完整版本放 trace/log，metric 只保留已發布的 release channel 或固定版本集合。

### 從一個 dashboard 問題開始

不要先畫十張 panel。先寫一個要回答的問題：本週 `insufficient_context` 上升，是知識庫覆蓋不足，還是 retrieval service 故障？

對應訊號可以是：

```text
answer_events_total by source_status
retrieval_duration_seconds histogram
retrieval_failures_total by error_type
deployment version / retrieval index version
```

判讀時需要把量與比例一起看。假如 `no_context` 從 1% 升到 10%，但問答流量剛好轉到新部門的政策問題，這可能是合理訊號；若同時 `retrieval_failures_total{error_type="timeout"}` 上升，才比較像可靠性問題。Metric 不會替你做結論，它只縮小值得查看 trace 和 log 的範圍。

### 以 trace 串起一次語意事件

在既有 OpenTelemetry trace 中，可為 workflow 增加低風險屬性：

```text
ai.workflow.name=policy_qa
ai.prompt.version=grounded-qa-v1
ai.retrieval.count=1
ai.answer.status=answered
ai.source.status=grounded
ai.contract.issue_count=0
```

不要直接把完整 prompt、answer 或 employee identifier 放進 span attribute。若 trace provider 或自架系統的 retention、存取權限尚未定義，先記版本與摘要，必要時在受控 log 中保留有限內容。可觀測性不是「把所有資料倒出去」的同義詞。

## 一個小型故障演練：故意讓回答看起來合理

好文章若只示範 happy path，讀者很容易在第一次模型自信胡說時才發現 contract 只是裝飾。以下四個演練都可在自己的 DIY 中以 fake model 或 fixture 完成，不必消耗任何付費模型 token。

### 演練一：引用不存在的文件

讓 fake model 回傳：

```python
CandidateAnswer(
    answer="每週可遠端三天。",
    cited_document_ids=["imaginary-policy-v9"],
)
```

預期：`source_status` 變成 `unsupported`，contract evaluator 回傳 `source_not_returned_by_retrieval`。HTTP 未必需要改成 500；這是回答品質事件，而非 FastAPI 崩潰。是否直接擋下回答，要依產品風險決定。

### 演練二：沒有文件卻裝作知道

讓 retrieval 回傳空清單，但 fake model 仍輸出有具體金額的答案。

預期：contract evaluator 至少回報 `answer_has_no_sources` 與 `answered_response_not_grounded`。如果 route 仍把它給使用者，這是你要在下一版 policy 中修的行為，不應讓 dashboard 把它塗成綠色。

### 演練三：retrieval timeout

讓 retrieval function 丟出已知的 dependency exception。

預期：`technical_status=failed` 或 `workflow_status=degraded`，並在 log/trace 記錄 dependency 類型。它和 `insufficient_context` 不同，因為系統沒有完成搜尋，不能誠實宣稱「文件沒有答案」。

### 演練四：parser 壞掉

讓模型輸出不是預期 JSON，或漏掉 `cited_document_ids`。

預期：在 model-output parser 邊界標成 `invalid_format`，保留安全的錯誤摘要；不要把原始 malformed output 靜默轉成空字串，再假裝它是資料不足。

這四種 case 的價值，在於它們讓不同 failure mode 有不同的語言、metric 和處置。不然 incident channel 最後只會出現一句「AI 壞了」，接著每個人各自猜。

## 哪些情況要 alert，哪些只該進 evaluation queue？

Semantic failure 並非都值得叫醒 on-call。Pager 是稀缺資源；把每筆 `unsupported` 都 page，通常只會讓真正的 model outage 被淹沒。

| 訊號 | 第一個處置 | 是否適合立即 page | 原因 |
| --- | --- | --- | --- |
| model provider 全面 timeout | incident response | 是 | 使用者無法取得服務 |
| retrieval dependency timeout 快速上升 | incident response | 視 SLO 與影響而定 | 可能是服務可靠性退化 |
| 單筆 `unsupported` answer | dataset / review queue | 通常否 | 需要先確認嚴重性與模式 |
| 高風險領域的錯誤建議 | policy escalation / human review | 可能是 | 影響取決於使用情境 |
| `insufficient_context` 緩慢升高 | product / knowledge-owner backlog | 否 | 多半是覆蓋率或需求變化 |
| parser invalid format 突增 | deployment investigation | 視比例而定 | 可能是模型或 schema 變更 |

一個務實的升級規則是：技術可用性用 online SLI/SLO 管；品質模式用抽樣評估與 release gate 管；高風險行為另外進 safety policy 和人工流程。Day 8 會把這三條線拆得更清楚。

## 本日可自行驗收的清單

完成自己的 DIY 後，可以逐項核對，而不是只在瀏覽器看見一段答案就收工：

- [ ] `/ask` 的成功回應有明確 `answer_status`，不是只有 HTTP status。
- [ ] 已分開 `EMPTY retrieval` 與 `FAILED retrieval`。
- [ ] 回答型結果的 `sources` 都來自同一次 `retrieved_document_ids`。
- [ ] 無資料情境會回 `insufficient_context`，不憑空補公司規則。
- [ ] 模型格式錯誤有自己的 failure path，不會被轉成假裝正常的空答案。
- [ ] 至少有一組可回答、不可回答、亂引來源與 dependency failure 的固定案例。
- [ ] 每筆案例可關聯 request ID、prompt version、retrieval index version 與 trace ID。
- [ ] Prometheus label 沒有 question、answer、request ID 或無限制增加的版本字串。
- [ ] dashboard 能區分資料覆蓋不足與 retrieval dependency 失敗。
- [ ] 團隊已決定哪些 semantic signal 進 queue、哪些依風險升級。

若其中任一項還沒有可觀察的證據，請把它標為未驗證，而不是補一句「理論上可以」。這個系列後面會一直把這種未知值當成工程工作，而不是寫作瑕疵。

## 今天刻意沒有解決的事

這個最小範例沒有處理多輪對話、citation passage-level verification、文件權限、prompt injection、模型 judge 的偏差、跨語言事實等價性或 human review queue 的 SLA。它也沒有宣稱 `grounded` 可以取代法律、人資、醫療或財務專業判斷。

keyword retrieval 只為了讓資料流可見。替換成 vector DB、hybrid search 或 reranker 後，`retrieval_result`、文件版本、查詢時間與 access control 仍要留在 contract 和 trace 中；演算法升級不會自動帶來可追溯性。

最重要的限制是 evaluator 也可能錯。若模型 judge 認為回答很好，但使用者或領域專家發現文件其實不支持它，應保存那個 review outcome，並將 evaluator 當作需要校準的元件，而不是裁判之神。

## 和下一篇的連接

Day 7 先把「技術成功」與「可採用的回答」拆開，並讓問題留下可查的足跡。Day 8 會接著問：Reliability、Quality、Safety 三者到底各自量什麼？哪一種失敗應由 SRE on-call 處理，哪一種應進 evaluation，哪一種必須先攔下來？

## 今天先帶走這個判斷式

```text
HTTP 200
≠ workflow is useful
≠ answer is grounded
≠ user completed the task
```

Day 8 會把 Reliability、Quality 與 Safety 分開談。它們互相影響，但不該混成一個分數：快速回覆錯誤規範，既不是高品質，也不會因為可用率很高就變得安全。

## 延伸閱讀

- [Google SRE：Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Google Research：What's your ML test score?](https://research.google/pubs/whats-your-ml-test-score-a-rubric-for-ml-production-systems/)
- [NIST AI RMF 1.0](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf)
- [Civil Resolution Tribunal：Moffatt v. Air Canada](https://decisions.civilresolutionbc.ca/crt/crtd/en/item/525847/index.do)
- [The Verge：Google AI Overviews 報導（2024）](https://www.theverge.com/2024/5/23/24162896/google-ai-overview-search-glue-pizza-cheese)
