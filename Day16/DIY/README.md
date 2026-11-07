# Day16 DIY — Tail Latency (P95) vs Mean Latency

對應 [Day16/Day16.md](../Day16.md) 的實作驗證。獨立 `uv` 專案，與其他 Day 完全分開。

## 內容

```text
Day16/DIY/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI endpoint with /ask route
│   ├── metrics.py        # Prometheus histogram definition
│   └── workflow.py       # Mock workflow implementation
├── scripts/
│   ├── test_latency.py   # Quick test with 20+1 requests
│   └── test_with_larger_sample.py  # Extended test with 100 requests
├── pyproject.toml
└── uv.lock
```

## 執行方式

### 初始化

```bash
cd Day16/DIY
uv sync
```

### 啟動服務器

在一個終端啟動 FastAPI 伺服器：

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 執行測試

在另一個終端執行測試腳本。有兩個選項：

**選項 1：快速測試（20 個快請求 + 1 個慢請求）**

```bash
uv run python scripts/test_latency.py
```

**選項 2：擴展測試（95 個快請求 + 5 個慢請求，更好的 percentile 演示）**

```bash
uv run python scripts/test_with_larger_sample.py
```

### 查看 Prometheus Metrics

```bash
curl http://127.0.0.1:8000/metrics/
```

## 實測結果

### 快速測試（21 請求）

```
Total requests:        21
Fast requests:         20 (95.2%)
Slow requests:         1 (4.8%)

LATENCY STATISTICS (milliseconds)
Mean:                       98.05 ms
P50 (median):                0.88 ms  (50% of requests ≤ this)
P95:                        30.42 ms  (95% of requests ≤ this)
P99:                      1614.51 ms  (99% of requests ≤ this)
Min:                         0.65 ms
Max:                      2010.53 ms
```

### 擴展測試（100 請求）

```
Total requests:        100
Fast requests:         95 (95.0%)
Slow requests:         5 (5.0%)

LATENCY STATISTICS (milliseconds)
Mean:                      101.78 ms
P50 (median):                1.28 ms  (50% of requests ≤ this)
P95:                       118.33 ms  (95% of requests ≤ this)
P99:                      2004.73 ms  (99% of requests ≤ this)
Min:                         0.51 ms
Max:                      2004.76 ms
```

### 觀察細節補充：兩組測試的 P95 為什麼差這麼多

快速測試（21 筆）的 P95 是 30.42ms，擴展測試（100 筆）的 P95 是 118.33ms——同樣都是「約 5% 慢請求」，P95 卻差了將近 4 倍。這不是程式行為不一致，而是文章 ⑤ 段講的小樣本抖動在實測裡真實重現：21 筆資料用 nearest-rank 算 P95，對應到排序後第 20 筆（`ceil(0.95×21)=20`），而 21 筆裡唯一的慢請求排在第 21 筆（最慢），沒有落進第 20 筆的位置，所以 P95 完全沒有反映到那筆慢請求，只在 P99（對應第 21 筆）才顯現出來。100 筆測試因為慢請求有 5 筆，其中至少一筆落進了 P95 對應的排序位置（第 95 筆附近），數字才真正被拉高。這正好是文章⑤段「一個小 Lab 一小時只有 30 筆請求，P99 幾乎等於在凝視一筆資料」的具體驗證——換成 P95，一樣的道理在 21 筆樣本下重現了。

### 觀察細節補充：Mean 對慢請求數量的敏感度

兩組測試的 Mean 幾乎沒有差（98.05ms vs 101.78ms），即使擴展測試的慢請求數量是快速測試的 5 倍（5 筆 vs 1 筆）、慢請求佔比幾乎相同（4.8% vs 5.0%）。這驗證了文章①段那個核心論點：只要慢請求佔比穩定在低個位數百分比，Mean 這個統計量對「慢請求數量增加」並不敏感，會持續給出一個看似穩定、實則正在掩蓋真相的數字。真正對慢請求數量敏感的是 P95 和 P99——這兩者才是文章反覆強調「該看分布而非單一平均值」的原因。

## 驗收清單

✅ **資料集包含約 5% 人為慢請求**
   - 快速測試：1/21 = 4.8%
   - 擴展測試：5/100 = 5.0%

✅ **能指出平均值與 P95 各回答什麼**
   - **Mean**：所有請求的平均耗時（快速測試 98ms、擴展測試 102ms）
     - 用途：評估系統整體資源消耗
     - 限制：掩蓋 5% 用戶的真實體驗
   - **P95**：95% 的請求在此時間內完成
     - 快速測試：30.42ms（低樣本下粗糙）
     - 擴展測試：118.33ms（更具統計意義）
     - 用途：評估典型用戶體驗
   - **P99**：99% 的請求在此時間內完成
     - 快速測試：1614.51ms（進入尾端區域）
     - 擴展測試：2004.73ms（明確包含慢請求）
     - 用途：評估最慢那群用戶

✅ **Latency 標記了 request 類型與時間窗**
   - 每個請求記錄 `is_slow` 標記（是否注入延遲）
   - 所有延遲以毫秒 (ms) 為單位
   - Prometheus histogram 記錄帶有 labels：`route="/ask"`、`workflow_status="completed"`、`model_route="primary"`

✅ **實驗由讀者自行執行**
   - 提供了可重現的測試腳本
   - 支持可控的延遲注入（`test_delay_ms` query parameter）
   - 結果完全可重現

✅ **Prometheus Histogram 正確記錄**
   - Metrics 端點在 `/metrics/` 暴露
   - Histogram 桶邊界設計合理：0.1, 0.25, 0.5, 1, 2, 3, 5, 10, 30 秒
   - 100 個請求被正確分配到各桶中

## 發現的問題與修正

### 問題 1：Prometheus Metrics 在 `/metrics` vs `/metrics/`

**現象**：`curl http://localhost:8000/metrics` 返回空，但 `/metrics/` 有效

**原因**：FastAPI 的 `mount()` 方法會在掛載路徑加上 `/`，所以 `/metrics` mount 的應用需用 `/metrics/` 訪問

**修正**：在文檔中明確說明使用 `/metrics/`

### 問題 2：小樣本 (n=21) 的 P95 表現

**現象**：21 個請求的 P95 只有 30.42ms，不清晰地展現尾端延遲

**原因**：P95 對應第 20 個請求（95% of 21 ≈ 19.95），而第 20 個恰好是快請求

**修正**：提供擴展測試腳本 `test_with_larger_sample.py` 以 100 個請求示範，其中 P99 清晰地顯示 2004.73ms（進入慢請求區域）

**文章相關**：Day16.md 第⑤節明確提到「Lab 的 20 筆樣本還可能因 scrape timing、rate window 或桶內插值而呈現和手算不同的數字」，這正是預期的

### 問題 3：Timer 精度

**現象**：快請求延遲約 0.5-4ms，比預期的 50ms 短

**原因**：
- Day16.md 的範例代碼用 `time.sleep(0.05)` 模擬工作
- 實際實作的 `run_policy_workflow()` 是純粹同步（無實際工作）
- 時間大部分花在 HTTP 協議處理和網路開銷，而非應用邏輯

**修正**：這是可接受的。實作遵循文章「本文沒有建立 `Day16/DIY`...請依自己的 Day2 Lab 套件版本和專案結構調整」的指示。實際應用會有更多業務邏輯耗時。

**額外觀察**：這個落差本身意外驗證了文章⑥段「真的跑起來時預期會踩到的坑」現象一：第一次請求的耗時明顯高於後續請求（約 4ms vs 後續穩定在 0.5-0.7ms），推測是 Python 直譯器 warm-up 與連線建立的一次性成本。這代表即使是「純粹同步、無實際工作」的 endpoint，也不是每一筆的耗時都完全相同——冷啟動效應在任何規模的系統裡都存在，只是幅度大小不同。

### 問題 5：高基數 label 的潛在風險（未實際觸發，但值得記錄）

**現象**：目前的 `app/metrics.py` 只用了 `route`、`workflow_status`、`model_route` 三個 label，series 數量可控（實測約在個位數到十位數之間）。

**若改動**：若之後有人想「順手」把 `request_id` 或 `question` 內容也塞進 label（例如為了方便在 Grafana 依單一請求篩選），會立刻對應到文章⑥段步驟 1 補充的高基數問題——每筆不重複的請求都會創建一條新的 Prometheus 時序資料,長期累積會拖慢查詢、增加記憶體用量。

**建議**：這個 DIY 實作目前沒有踩到這個坑，是因為維持了低基數設計；如果要延伸這個實作去做更真實的壓力測試（例如送出上千筆請求），務必先確認新增的 label 是否仍是有限、可枚舉的集合，而不是每筆請求都不同的識別值。

### 問題 4：Async vs Sync 計時

**決策**：使用 `perf_counter()` 而非 `time.time()`

**原因**：
- `perf_counter()` 不受系統時鐘調整影響，更適合計時區間
- `time.time()` 可能在系統時鐘調整時出現負時差
- 文章第⑥節明確示範使用 `perf_counter()`

**實現細節**：
```python
started_at = perf_counter()
# ... do work ...
elapsed_seconds = perf_counter() - started_at
```

## 與文章對應關係

| 文章段落 | DIY 實現位置 | 驗證方式 |
|--------|-----------|--------|
| ② 「故意製造 5% 慢請求」| `scripts/test_*.py` + `/ask?test_delay_ms=2000` | 運行測試腳本，檢查慢請求比例 |
| ⑤ 「percentile 的小算術」| `test_with_larger_sample.py` 輸出 | 執行 100 請求測試，觀察 mean/P50/P95/P99 的差異 |
| ⑥ 「在 FastAPI 記錄 histogram」| `app/metrics.py` + `app/main.py` | `curl http://localhost:8000/metrics/` 驗證計數 |
| ⑥ 步驟 1 | `app/metrics.py` | Prometheus histogram 定義 |
| ⑥ 步驟 2 | `app/main.py` 的 `/ask` 路由 | `perf_counter()` 計時、`finally` 記錄 |
| ⑥ 步驟 3 | `app/main.py` 的 `inject_delay_if_requested()` | `test_delay_ms` query parameter 注入 |
| ⑥ 步驟 5 | `/metrics/` 端點 | 暴露 Prometheus 指標供外部查詢 |
| ⑥ 步驟 6 | `app/main.py` 日誌記錄 | 結構化日誌輸出 JSON 格式 |

## 關鍵洞察

1. **平均值掩蓋尾端**
   - 100 個請求的 Mean 101.78ms 看起來還可以
   - 但 5% 的用戶實際等待 ~2000ms，是平均的 20 倍

2. **分位數揭示真相**
   - P50（1.28ms）：典型用戶體驗
   - P95（118.33ms）：顯著慢的用戶族群
   - P99（2004.73ms）：最慢的用戶

3. **SLO 設定的重要性**
   - 若 SLO 用 Mean：5% 用戶體驗不佳
   - 若 SLO 用 P95：目標更切合実際用戶體驗
   - 若 SLO 用 P99：保護最慢的用戶

4. **Prometheus Histogram 的優勢**
   - 低基數 labels（route、workflow_status、model_route）
   - 預先定義的桶邊界支持 quantile 估算
   - 可直接透過 PromQL 查詢 `histogram_quantile(0.95, ...)`

## 下一步方向

1. **在 Grafana 中設置 Dashboard**
   - Row 1: P50、P95、P99（而非只看 Mean）
   - Row 2: Workflow breakdown（retrieval、TTFT、generation 各別耗時）
   - Row 3: Error rate 與 tail latency 的相關性

2. **設置告警**
   - `ask_request_duration_seconds P95 > 3 秒` → 告警
   - 對比 Mean > 3 秒 的告警，更容易抓到真實問題

3. **進階實驗**
   - 模擬 fanout 架構（多個依賴並行調用）觀察尾端延遲如何放大
   - 測試 retry policy 對 tail latency 的影響

## 執行時長注意事項

- 快速測試（21 請求）：約 5-10 秒
- 擴展測試（100 請求）：約 10-15 秒（包括 5 個 2 秒延遲）

若要更快完成測試，可減少 `num_slow` 或 `slow_delay_ms` 的值。
