# Day 09 DIY — Service Boundary 規格檢查

驗證 [Day9.md](../Day9.md) ⑨ 的 DIY 段落。

Day9.md 本身聲明「本文沒有建立 `Day9/DIY`、安裝依賴、啟動服務或執行以下檢查，因此不宣稱任何程式或架構已驗證」，因為這篇文章談的是設計練習（畫 Service boundary），不是可執行的服務。本目錄依 repo `CLAUDE.md` 的 DIY SOP，把文章 ⑨ 的 Step 1-4 練習變成一份實際填寫的規格檔（`service_boundary.yaml`），再寫一支驗證腳本，對照文章 ⑩ 的概念驗收清單做結構檢查——驗證的不是「程式行為對不對」，而是「這份 Service boundary 文件有沒有把該填的欄位填齊」。

對象沿用 Day7/Day8 的 Grounded Q&A `/ask` 服務（查詢差旅政策），維持系列文章之間的連續性。

## 內容

```text
Day9/DIY/
├── pyproject.toml
├── service_boundary.yaml       # Day9.md ⑨ Step 1-4 的填寫結果
├── app/
│   ├── __init__.py
│   └── validator.py            # 對照文章⑩驗收清單的結構檢查邏輯
└── scripts/
    └── validate_boundary.py    # 讀 yaml，跑 validator，印 PASS/FAIL
```

## 執行方式

```bash
cd Day9/DIY
uv sync
uv run python scripts/validate_boundary.py
```

## 實測結果

- [x] `uv sync` 成功解析並安裝所有相依套件（`pyyaml` 6.0.3）
- [x] `uv run python scripts/validate_boundary.py` 對 `service_boundary.yaml` **全部 11 項檢查通過**：
  - service contract 是一句使用者結果，不是元件名稱
  - critical path 從 Client 畫到 Response，共 6 個節點
  - 4 個依賴（Retriever／LLM Provider／Validator／Control Plane）都填齊 owner、required、expected_failure_behavior、observable_signal
  - 依賴清單裡有涵蓋 monitoring/deployment 這類 control plane 能力（對應文章 ⑩ 的第 6 項勾選項）
  - 3 個候選 SLI 都有明確 `PROVEN`/`UNKNOWN` 狀態與理由，且至少一個誠實標成 `UNKNOWN`（對應文章 ⑩ 的第 7 項勾選項）
- [x] 額外用一份刻意留白的規格（缺 service_contract、critical_path 只有 1 個節點、依賴缺欄位、沒有 control plane 依賴、沒有任何 UNKNOWN 訊號）餵給 `validate()`，確認驗證腳本**會正確回報 FAIL**，不是永遠綠燈的假檢查

## 發現的問題與修正

1. **Day9.md 的驗收清單（⑩）本身是給人看的敘述句，不是可執行的規則**：例如「確認 monitoring、deployment、authorization 等 control plane 能力是否也在 failure model 裡」沒有定義「確認」要怎麼量化。本 DIY 把它簡化成關鍵字比對（`app/validator.py` 的 `CONTROL_PLANE_KEYWORDS`），這跟文章 ⑤⑦ 反覆強調的「關鍵字比對有天生侷限」是同一種限制——這支腳本能抓出「完全沒提到 control plane」的明顯遺漏，但抓不出「提到了但寫得敷衍」的情況，仍需要人工判斷。

2. **「至少一個 UNKNOWN」這條檢查是本 DIY 自行加上的延伸，不是文章逐字要求**：文章 ⑩ 第 7 項只要求「把觀測到、但尚未能代表使用者結果的訊號標成 UNKNOWN」，沒有明講「至少要有幾個」。本 DIY 額外加了「至少一個候選 SLI 是 UNKNOWN，否則提醒可能過度樂觀」，這是把文章 ⑦ 的精神（不要把 proxy 當真相）轉成一條可執行規則，如果某個服務的候選訊號真的全部都已被證實，這條檢查會誤報，需要人工判斷是否合理。

3. **驗證對象是規格檔本身，不是任何正在運行的服務**：這支腳本不會真的去 curl `/ask` 或檢查 Day8/DIY 的服務是否符合 `service_boundary.yaml` 描述的行為——它只驗證「文件有沒有寫齊」，不驗證「系統實際行為是否符合文件」。要做到後者，需要另外寫整合測試對照 Day8/DIY 的 API 回應，這超出 Day9.md 本身的範圍。

## 證據邊界

本次驗證證明：`service_boundary.yaml` 的結構完整（欄位齊全、control plane 有被涵蓋、SLI 候選誠實標註），以及 `app/validator.py` 的檢查邏輯本身正確（用正例與刻意留白的反例都測過）。**未驗證**：`service_boundary.yaml` 裡描述的 failure behavior（例如「Retriever 找不到資料時明確回覆資料不足」）是否真的符合 Day8/DIY 服務的實際行為——這需要對照 Day8/DIY 的程式碼或跑一次真實請求才能確認，不在本 DIY 範圍內。
