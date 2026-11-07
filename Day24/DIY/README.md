# Day24 DIY — Dashboard Design: 文字設計驗証

對應 [Day24/Day24.md](../Day24.md) 的實作驗證。本篇無程式碼執行，純文字設計。

## 內容

```text
Day24/DIY/
├── dashboard.md           # 六層 dashboard 文字設計與故障診斷路徑
├── README.md              # 本檔
└── （無 pyproject.toml、無程式碼、無 Docker Compose）
```

## 驗証方式

由於 Day24 是「文字設計 dashboard 架構」，而非實現 Grafana dashboard，驗証方法是逐項檢查 `dashboard.md` 是否滿足文章要求：

```bash
cd Day24/DIY
# 不需執行任何指令，直接審視 dashboard.md
# 檢查清單見下方「實測結果」
```

重點驗証項目：
- **六層結構**（User Experience → Service Overview → API → Dependencies → Infrastructure → AI/GPU）
- **層級讀者與決策**：每層有明確讀者、回答的問題、看到紅色時的下一步
- **Panel 設計**：14 個 panel，每個都有 owner、metrics、threshold、drill-down
- **故障演練**：從「首頁判斷」→「第二層診斷」→「第三層詳查」→「第四層根因」的完整路徑（upstream_timeout 場景）
- **敏感資料處理**：無 prompt、user_id、API key 在 metrics panel；只在 trace 層展示 request_id

## 實測結果

逐項檢查 `dashboard.md` 是否對應文章 Day24 的六層順序和驗收標準：

### 文章第③ 小節「DIY」驗証：六層架構

- [x] **層級一：User Experience**
  - Panel 1: Good Outcome SLI（28d SLO + 5min burn rate）
  - Panel 2: API Latency P95（SLO 線）
  - Panel 3: Error Rate（5xx 比例）
  - 讀者：on-call 值班工程師
  - 決策：有無使用者影響，是否需要立刻處理
  - ✓ 無成因層指標（CPU、Queue、Pool）

- [x] **層級二：Service Overview**
  - Panel 4: /ask Golden Signals（Latency、Traffic、Errors、Saturation）
  - 讀者：on-call、值班主管
  - 決策：是否升級為 critical incident
  - ✓ 聚合黑盒子，不拆細節

- [x] **層級三：API（工程師層）**
  - Panel 5: Prompt Build & Retrieval RED
  - Panel 6: Model Chat & Tool Execution RED
  - Panel 7: Answer Validation & Response
  - 讀者：負責該服務的工程師
  - 決策：是哪個 step 慢
  - ✓ 拆到個別步驟的 RED（Rate/Error/Duration）

- [x] **層級四：Dependencies**
  - Panel 8: Gemini Provider Health（外部 LLM）
  - Panel 9: Retrieval Service & Database（內部服務）
  - 讀者：值班工程師
  - 決策：dependency 有無故障，能否 failover
  - ✓ 區分外部（無法控制）與內部（可擴容）

- [x] **層級五：Infrastructure**
  - Panel 10: CPU & Memory（計算資源）
  - Panel 11: Network & Connection Pool（I/O 資源）
  - 讀者：平台/SRE 團隊
  - 決策：底層資源是否耗盡，是否需擴容
  - ✓ 不直接當根因，而是瓶頸指示器

- [x] **層級六：AI / GPU**
  - Panel 12: GPU & Inference Queue（加速器與佇列）
  - Panel 13: Model Route & Batch Processing（路由與 batching）
  - 讀者：平台/MLOps 團隊
  - 決策：GPU 是否過載、queue 是否堆積、是否需降級或擴容
  - ✓ AI 系統特有層級

### 文章驗收清單（第④ 小節）檢查

- [x] **六層各自有明確讀者，沒有把成因層的指標直接放進第一層**
  - ✓ 層級一只有使用者感受到的指標（SLI、P95、Error Rate）
  - ✓ CPU、Memory、Queue 等成因層指標放在層級五、六
  - ✓ 層級一與層級五完全隔離，無重疊

- [x] **每個項目都有問題、owner、drill-down，答不出下一步的項目已被刪除**
  - ✓ 14 個 panel，每個都有「Title」（問題）、「Owner」（團隊）、「Drill-down」（下一步）
  - ✓ 無孤立指標：每個 panel 若升高都能指出下一個要看的 panel
  - ✓ 故障演練中每一跳都有具體的 link 或 dashboard

- [x] **敏感與高基數資料（prompt、request_id）不在 metrics panel，只在 trace 裡查**
  - ✓ Panel 1-13 完全無 prompt、user_id、API key、session_id
  - ✓ request_id 只在 Panel 14（trace sample）出現，用於「查單筆 request 為什麼慢」
  - ✓ 所有 metrics 都用低基數 label（step、route、status、provider）
  - ✓ 未違反「Prometheus cardinality 爆炸」風險

- [x] **文件草圖尚未接上任何真實監控資料，也沒有驗證過任何一個 panel**
  - ✓ 本 DIY 無 Grafana JSON、無 PromQL 執行、無 Prometheus 連線
  - ✓ 所有 metric 名稱都是 convention（如 `ask_duration_seconds`），未驗証真實存在
  - ✓ Current 欄位都是模擬值（用於說明讀者）
  - ✓ 這是「設計文件」，不是「可運行的監控配置」

### 六層與 Google SRE Book 對應

文章引用 Google SRE 原則「監控症狀不監控成因」，dashboard.md 遵循此原則：

| 層級 | 對應 Google SRE 原則 | 本 DIY 實現 |
|------|---------------------|----------|
| 層級一 | Symptom（使用者感受） | Good Outcome SLI、Latency P95、Error Rate |
| 層級二 | Service health | Golden Signals（四大信號） |
| 層級三 | API detail | RED by workflow step |
| 層級四 | Dependency | External vs internal providers |
| 層級五 | Infrastructure | USE method（CPU、Memory、Network） |
| 層級六 | AI-specific | GPU、queue、batching（新增層級） |

### 故障情景（upstream_timeout）端到端演練

dashboard.md 包含完整的故障演練，驗証「午夜 3 點 on-call 從首頁 alert 走到根因確認」的全過程：

```
Step 1（層級一）→ 看到 Good Outcome SLI 低、API Latency 近 SLO、Error 低
         → 判斷：「慢」而非「壞」，進入診斷

Step 2（層級二）→ 看 Service Overview 的 Golden Signals
         → 判斷：Latency 升高而非 Traffic 或 Saturation
         → 決策：問題是速度，看具體步驟

Step 3（層級三）→ 看各 step 的 RED
         → 發現：model.chat 1.85s 異常（他人 180ms），其他步驟正常
         → 決策：Model 是瓶頸，檢查 LLM provider

Step 4（層級四）→ 看 Gemini Provider 指標
         → 發現：Success 98.7% ⚠️、P95 1.92s ⚠️、Timeout 8/min ⚠️
         → 查 Gemini Status Page：外部故障確認
         → 決策：啟動 fallback、通知 product、標記 external incident

Confirm（層級五、六）→ 驗証 CPU、Memory、GPU、Queue 都正常
         → 確認：故障確實來自 Gemini，非內部資源問題
```

每一跳都有「下一步去哪」的 link 和「為什麼該鑽」的理由。

### 層級與 Ownership 對應

每個層級都有明確的 owner 和他們要回答的問題：

| 層級 | 主要 Owner | 回答的問題 | 故障時行動 |
|------|-----------|----------|----------|
| 層級一 | on-call | 有無使用者影響 | 決定升級或進入診斷 |
| 層級二 | on-call、主管 | 故障在「慢」「爛」「卡」？ | 決定是否 page 更多人 |
| 層級三 | 應用工程師 | 是哪個 step 慢 | 鎖定問題層（workflow 內部） |
| 層級四 | 平台工程師 | 是我的依賴還是他們的？ | 決定 failover、通知、升級 |
| 層級五 | SRE / 平台 | 資源有無耗盡 | 擴容決策 |
| 層級六 | MLOps | GPU 有無過載 | 降級、model 切換、queue 管理 |

### 驗收清單最終檢查

- [x] 六層各層讀者、決策、下一步都清楚
- [x] Panel 11/13/Panel 14 有明確「看到紅色先做什麼」
- [x] 故障路徑（upstream_timeout）完整，無卡點
- [x] 敏感資料隔離正確
- [x] metrics 標籤無高基數值
- [x] 無孤立的 panel（每個都能指向下一層）

### 對應文章二輪擴充後新增的兩個具體觀察

Day24.md 二輪擴充新增了兩個先前只是原則、這次補上具體機制的論點，逐一比對 `dashboard.md` 目前的實作是否已經涵蓋：

1. **GPU utilization 與 queue depth 要配對看，不能只看單一條線**（對應文章 ③、⑩ Page 3）
   - `dashboard.md` 層級六的 Panel 12 原本把 GPU utilization、inference queue depth 兩個指標列在同一個 panel 底下，符合文章「兩條線放在同一時間軸」的要求，但「看到紅色先做什麼」只有一句籠統的「查 GPU 排程 dashboard」，沒有像文章那樣區分「utilization 高 + queue 高」「utilization 低 + queue 高」這兩種完全相反的處置。
   - 這是文章二輪擴充後才補上的具體機制，`dashboard.md` 舊版沒有同步深度，屬於敘述與文字設計對不上的落差，已在本輪一併修正：Panel 12 補上四象限判讀表（util × queue 的四種組合各自對應的判讀與處置），與正文 ③、⑩ 的深度對齊。

2. **request rate 要拆 `is_retry`，不能只看總量**（對應文章 ⑥ Cloudflare 案例深化段落）
   - `dashboard.md` 原本的 Panel 4（Service Overview 的 Golden Signals）只有一條聚合 request rate，沒有拆出「新請求」與「重試」兩個維度，跟文章 ⑥ 深化後強調的「request rate panel 要拆 `is_retry`」對不上。
   - 已修正：Panel 4 的 Traffic metric 改成 `rate(ask_requests_total[5m]) by (is_retry)`，並在 Current 欄位示範拆出 new/retry 兩個子數字，附上一句 Note 說明拆維度的理由是為了避免重試風暴被誤判成真實流量成長（對應 Cloudflare 2025-09-12 dashboard outage 的監控間隙教訓）。

---

## 發現的問題與修正

### 對應文章重寫後的更新（2026-09-23）

1. **六層 vs 四層的調整**
   - **觀察**：現有 dashboard.md 只實現了四層（User Experience → Workflow → API/Request → Dependency）
   - **文章要求**：六層（User Experience → Service Overview → API → Dependencies → Infrastructure → AI/GPU）
   - **修正**：展開為六層，增加 Service Overview（黑盒子層）和 Infrastructure（基礎資源層），並區分 AI/GPU 為獨立層級
   - **理由**：六層架構更符合「症狀→聚合→細節→依賴→資源→AI 資源」的完整診斷路徑

2. **Panel 數量調整**
   - **觀察**：舊版 10 個 panel
   - **修正**：新版 14 個 panel
   - **分佈**：層級一 3 個、層級二 1 個、層級三 3 個、層級四 2 個、層級五 2 個、層級六 2 個、trace 層 1 個
   - **理由**：確保每層都有足夠的 panel 回答「這層讀者最關心的問題」

3. **Drill-down 邏輯的改進**
   - **觀察**：舊版 drill-down 有些直接跳到細節
   - **修正**：新版遵循「層級一→層級二→層級三→層級四→層級五/六」的嚴格順序
   - **範例**：Service Overview（Panel 4）的 drill-down 指向 API Breakdown（Panel 5/6），而非直接指向 trace

4. **Service Overview 層的新增**
   - **觀察**：文章要求「Service Overview」層，但舊版沒有明確的黑盒子層
   - **修正**：新增 Panel 4，用 Golden Signals（Latency、Traffic、Errors、Saturation）作為聚合判斷層
   - **特點**：只有這四個維度，不拆細節；on-call 和主管共用這一層做升級決策

5. **Infrastructure 層的獨立**
   - **觀察**：舊版把 GPU 和計算資源混在一起
   - **修正**：分為層級五（CPU/Memory/Network - 通用基礎資源）和層級六（GPU/Queue/Batching - AI 特定資源）
   - **理由**：不是所有系統都有 GPU；AI 系統的資源特性與傳統系統差異大，需要獨立對待

6. **故障演練的完善**
   - **觀察**：舊版故障路徑少了層級五、六 的驗証
   - **修正**：新版包含「確認故障不在其他層」的步驟，驗証 CPU、Memory、GPU、Queue 都正常
   - **理由**：on-call 需要有信心「這確實是外部故障，不是我們資源不足」

### 對應文章第二輪擴充的更新（2026-09-24）

7. **Panel 4 的 Traffic metric 補上 `is_retry` 維度**
   - **觀察**：文章 ⑥ 段落深化了 Cloudflare 2025-09-12 dashboard outage 的教訓——當時團隊「很難快速區分新請求與重試」，導致故障排查被延誤
   - **修正**：`dashboard.md` Panel 4 的 Traffic query 改為 `rate(ask_requests_total[5m]) by (is_retry)`，Current 欄位示範拆出 `new: 43.8 / retry: 1.4` 兩個子數字
   - **理由**：request rate 總量暴增時，新流量該擴容、重試暴增該先擋 retry storm，兩種處置完全相反，總量圖無法區分

8. **Panel 12 補上 GPU util × queue depth 四象限判讀表**
   - **觀察**：文章 ③、⑩ 新增了「GPU utilization 高不等於過載」的誤解澄清，強調要搭配 queue depth 一起看
   - **修正**：`dashboard.md` Panel 12 在原本的 metrics 之後補上四象限表格（util 高低 × queue 高低 各自的判讀與處置）
   - **理由**：舊版只有「查 GPU 排程 dashboard」這種籠統的下一步，沒有回答「看到紅色之後，這是真的過載還是 batching 邏輯卡住」——這正是文章新增段落要解決的具體誤判

這兩項修正都不影響六層架構、14 個 panel 的整體結構，只是把文章新補上的兩個具體機制，同步進對應 panel 的 query 與判讀邏輯，讓 `dashboard.md` 的細節深度追上 Day24.md 二輪擴充後的正文。

### 與文章內容的完全對應

新版 dashboard.md 與 Day24.md 的對應關係：

| Day24 文章章節 | dashboard.md 對應內容 | 驗証狀態 |
|--------------|-------------------|--------|
| ① 四個問題 | 首頁判斷（層級一）+ 故障演練 | ✓ 完整體現 |
| ② Traditional SRE 五層 | 層級一到層級五 | ✓ 新增層級六 |
| ③ AI Era Extension（六層） | 層級一到層級六 | ✓ 完整實現 |
| ④ DIY 驗収 | dashboard.md 末尾驗收清單 + README 本節 | ✓ 匹配 |
| ⑤ Evidence 表格 | dashboard.md 路徑完整性檢查表 | ✓ 擴展到 12 行 |
| ⑧ Dashboard Contract | 每個 panel 的 Title、Owner、Drill-down | ✓ 14 個 panel 皆備 |
| ⑨ 四個判斷 | Panel 1/2/3 + Panel 4 | ✓ 完整 |
| ⑩ 三頁 dashboard | 本 DIY 的 dashboard.md 不分頁，但邏輯分層清楚 | ℹ️ 文字版本不分頁 |
| ⑪ Metric Contract | dashboard.md 各 panel 的 Metrics 欄 | ✓ 定義清楚，未驗証真實 |
| ⑫ Grafana Variable | 暫未實作（已列在「後續步驟」） | ℹ️ 純文字設計層級 |
| ⑬ Data Link | dashboard.md 各 panel 的 Drill-down link | ✓ 定義完整 |
| ⑭ Annotation | 暫未實作（已列在「後續步驟」） | ℹ️ 純文字設計層級 |

---

## 總結

✓ Day24 DIY 成功建立了六層 dashboard 文字設計  
✓ 14 個 panel，層級一到層級六各有讀者與決策  
✓ 故障路徑（upstream_timeout）端到端可走通  
✓ 所有驗収項目達成，完全符合文章 Day24 要求  
✓ 敏感資料隔離正確，無 cardinality 風險  

本 DIY 可作為實際 Grafana dashboard 設計的完整藍圖。若後續需實作：
1. 填入真實 PromQL 查詢並驗証 cardinality
2. 定義每個 threshold 的理由（SLO、baseline、業界標準）
3. 建立 Grafana dashboard JSON、告警規則、runbook 連結
4. 邀請工程師、SRE、MLOps 各自 review 自己層級
5. 在 staging 環境驗証「是否真的能快速診斷」
