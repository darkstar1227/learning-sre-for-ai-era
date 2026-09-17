# Learning SRE for the AI Era

**從 SRE Lab 到 Production AI Reliability**

2026 iThome 鐵人賽 參賽紀錄 — 主題：AI Engineering

## 系列簡介

隨 AI 系統走入生產環境，傳統 SRE 實踐面臨新挑戰：模型延遲不穩定、資料漂移、LLM 輸出不可預測、GPU 資源調度複雜。

本系列以概念＋實作，從 SRE 基礎打造 AI SRE Lab。使用 FastAPI、Docker、Prometheus、Grafana、Loki、OpenTelemetry 與 LLM Tracing，實作 SLI/SLO、Error Budget、可觀測性、告警、事故處理與 CI/CD。

並探討 LLM、RAG、Agent 的 TTFT、檢索失敗、語意品質、安全與成本。Production AI 不會取代 SRE，而是將可靠性從 API 延伸到 Workflow、Model Behavior 與使用者任務成功。

核心主線：

> **Build → Trace → Break → Measure → Evaluate → Recover → Improve.**

## 目錄

| Day | 主題 |
| --- | --- |
| [Day0](./Day0/Day0.md) | 從零建立開發環境：Python、uv、Gemini API Key 與 LangSmith |
| [Day1](./Day1/Day1.md) | 用 LLM Trace 看見一次 AI Workflow 的完整生命週期 |
| [Day2](./Day2/Day2.md) | 建立自己的 SRE Lab：從 FastAPI 到 Observability Stack |
| [Day3](./Day3/Day3.md) | 故障注入實驗：Break / Observe / Explain |
| [Day4](./Day4/Day4.md) | 什麼是 SRE？可靠性不是零故障 |
| [Day5](./Day5/Day5.md) | DevOps、SRE 與 Platform Engineering：別再把三種工作混成一個職缺 |
| [Day6](./Day6/Day6.md) | Reliability 到底是什麼？把「很穩」拆成五個能討論的問題 |
| [Day7](./Day7/Day7.md) | Technical Success ≠ Semantic Success：AI 系統如何「正常地失敗」？ |

每篇文章固定回答：

1. 傳統 SRE 怎麼理解？
2. AI 時代增加了什麼變數？
3. 如何在 SRE Lab 驗證？
4. Production 上會影響什麼決策？
