import json
import logging
import sys


logger = logging.getLogger("ai_evaluation")
logger.setLevel(logging.INFO)

if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(_handler)
    logger.propagate = False


def log_evaluation(**fields: object) -> None:
    """對應 Day8.md 段落 ⑦ 的 structured log 範例。

    本 DIY 未接 Day2/Day6 的 OTel/Loki 堆疊，這裡只印一行 JSON 到 stdout，
    欄位命名與文章一致，方便之後直接接進既有 observability pipeline。
    """
    logger.info(
        json.dumps(
            {"event": "ai_response_evaluated", **fields},
            ensure_ascii=False,
        )
    )
