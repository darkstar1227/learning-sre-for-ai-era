# Rollback Card Template

Based on Day28.md section ⑪ (Rollback Card)

## Rollback Card: answer-v17

### Trigger

- `citation_valid_rate < 0.98`
- 任一 safety case 在 canary 被人工確認為漏攔
- Error rate spike > 0.5% above baseline

### Immediate Mitigation

- 停止下一階段 promotion
- 將新 session route 切回 answer-v16
- 通知 on-call 與產品負責人

### Do NOT Do Without Approval

- 不關閉 citation validator
- 不把 timeout 全域拉長
- 不修改 fallback behavior 來隱蓋問題

### Compatibility Check

- [x] answer-v16 可讀取目前 metadata 欄位
- [x] policy-tools-v4 不會被 answer-v16 呼叫（v4 是新增的）
- [x] 舊版 retrieval index 仍然可用

### Recovery Evidence

- 新進 request 的 citation_valid_rate 連續 30 分鐘回到 baseline（≥0.95）
- 抽查 10 筆不同 question type 的 trace，版本欄位均為 answer-v16
- No new incidents in on-call channel during rollback window

### Post-Incident Actions

- [ ] Root cause analysis for any policy-042 failures
- [ ] Update golden dataset with new edge case
- [ ] Schedule post-mortem if customer impact confirmed
