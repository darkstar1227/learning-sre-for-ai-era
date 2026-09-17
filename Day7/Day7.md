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
