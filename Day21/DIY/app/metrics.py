"""Prometheus metrics with low-cardinality labels."""

from prometheus_client import Counter

# metrics label 要低基數：只放 outcome 這種固定幾個值的欄位
# 絕不要放 request_id、prompt、document_id、user_id 等高基數值
timeout_incidents = Counter(
    "dependency_timeout_incidents_total",
    "Total dependency timeout incidents",
    labelnames=["dependency"],  # dependency name: retriever, model, tool, etc.
)

# 追蹤是否成功回答
answer_requests = Counter(
    "answer_requests_total",
    "Total answer requests",
    labelnames=["outcome"],  # outcome: success, timeout, error, refused
)
