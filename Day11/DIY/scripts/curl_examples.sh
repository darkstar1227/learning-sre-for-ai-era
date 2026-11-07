#!/bin/bash

# 手動測試 Day11 DIY API 的腳本
# 對應文章情境一（慢 provider 與 deadline）與情境二（retry amplification）
#
# 使用方式：
#   1. 終端 1：cd Day11/DIY && uv run uvicorn app.main:app --reload
#   2. 終端 2：bash scripts/curl_examples.sh

BASE_URL="http://127.0.0.1:8000"

echo "=========================================="
echo "Day11 DIY - Failure Mode 測試"
echo "=========================================="

# 情境一：正常請求
echo -e "\n[1] 正常請求 (failure_mode=normal)"
curl -i "${BASE_URL}/ask" \
  -H 'content-type: application/json' \
  -d '{"question":"Can I work remotely?"}'

# 情境一：慢 provider（應該 timeout）
echo -e "\n\n[2] 慢 provider (failure_mode=slow) - 預期 HTTP 503"
curl -i "${BASE_URL}/ask" \
  -H 'content-type: application/json' \
  -d '{"question":"Can I work remotely?","failure_mode":"slow"}'

# 情境二：不可用 provider（無 retry）
echo -e "\n\n[3] 不可用 provider (failure_mode=unavailable) - 無 retry"
curl -i "${BASE_URL}/ask" \
  -H 'content-type: application/json' \
  -d '{"question":"Can I work remotely?","failure_mode":"unavailable"}'

# 情境二：不可用 provider（有限 retry）
echo -e "\n\n[4] 不可用 provider (failure_mode=unavailable) - 帶 retry budget"
curl -i "${BASE_URL}/ask/with-retry" \
  -H 'content-type: application/json' \
  -d '{"question":"Can I work remotely?","failure_mode":"unavailable"}'

echo -e "\n\n=========================================="
echo "測試完成"
echo "預期結果："
echo "  [1] HTTP 200，answer_status='answered'"
echo "  [2] HTTP 503，answer_status='unavailable'"
echo "  [3] HTTP 503，answer_status='unavailable'"
echo "  [4] HTTP 503，answer_status='unavailable'（最多 2 attempt）"
echo "=========================================="
