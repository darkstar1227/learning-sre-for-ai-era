# answer-api availability SLO

## SLI（服務等級指示）

有效 `/ask` 在 10 秒內取得可用結果或明確狀態的比例。

**定義**：`good events / valid requests`

### Good Event（分子）

下列任何狀態都視為成功：
- `completed`：模型完成回答
- `insufficient_context`：模型明確表示資訊不足，無法回答
- `requires_human_review`：轉給人工審查

**且**：
- 必須在 10 秒內完成
- HTTP 200 OK（不是 5xx）

### Valid Request（分母）

分母包含所有非負載測試的 `/ask` 請求。

**包含**：
- 所有未標記為負載測試的 user request

**排除**：
- 明確標記的負載測試（待定標記方式）
- 系統 synthetic healthcheck（如果可分離的話）

### Bad Event

以下任何情況都算失敗：
- 未在 10 秒內完成
- HTTP 5xx 錯誤
- 無法辨識的 response contract（既不是上述 3 個 good event，也不是明確的技術錯誤）

### 初始 SLO（假設）

- **目標**：待用實際資料與產品負責人確認
- **時間窗口**：28 天 rolling window

## SLO（服務等級目標）

團隊內部承諾：在設定時間窗口內，SLI 指標應達到目標百分比。

目標值 **待確認**，初步考慮：
- 保守估計：99.0%（每月 ~7.2 分鐘停機預期）
- 進階目標：99.5%（每月 ~3.6 分鐘停機預期）

## SLA（服務等級協議）

對外客戶承諾（如有合約）。

**目前**：未簽署客戶 SLA，故本欄位 N/A

## 資料來源與監控

- **收集方式**：Application logs（每個 request/response 記錄 status、duration）
- **儲存**：（待決定）Prometheus metrics + Loki logs
- **查詢**：（待建立）PromQL for SLI calculation
- **頻率**：每 5 分鐘 evaluate 一次

範例 PromQL（未來）：
```promql
sum(rate(ask_responses_good{service="answer-api"}[5m])) 
/ 
sum(rate(ask_responses_valid{service="answer-api"}[5m]))
```

## 負責人與審查

- **Owner**：待指派
- **最後審查日期**：待設定
- **下次審查日期**：待設定（建議 30 天）

## 待確認項目（Checklist）

- [ ] 與產品確認「10 秒」是否為合理 SLA
- [ ] 決定負載測試的標記方式（Header / Request ID pattern / 其他）
- [ ] 確認 good event 狀態碼是否只有 `200`（或是否應包含 `202 Accepted`）
- [ ] 確認分子/分母的排除條件是否完整
- [ ] 與客戶簽署 SLA 時，是否需要調整 SLO 邊界
- [ ] 建立 Prometheus metrics 與 Grafana dashboard
- [ ] 設定 error budget 告警（e.g., 用完 50% 時 page on-call）

## 注意事項

1. **百分比本身沒有意義**：99.9% 可用性在理論上每月停機 43.8 分鐘，但實際業務影響取決於停機是否集中/分散，以及隱藏依賴（如 DNS 故障）是否納入 SLA 定義。

2. **分母定義先決**：排除條件（e.g., 負載測試）必須公開、可實作、可稽核。不確定的項目寧可先納入分母，之後有數據後再調整。

3. **SLO vs SLA**：
   - SLO：團隊內部目標（可調整）
   - SLA：對客戶的法律承諾（嚴格）
   - 不要直接把內部 SLO 貼進客戶合約。

## 參考資料

- Google SRE: [Implementing SLOs](https://sre.google/workbook/implementing-slos/)
