"""
Example runbook entries for common incidents.

These demonstrate the runbook structure described in Day27.
"""

from app.models import RunbookEntry
from app.templates import generate_runbook_markdown


def create_example_runbook_entries() -> list[RunbookEntry]:
    """Create a set of example runbook entries for common SRE issues."""

    entries = [
        RunbookEntry(
            issue_name="Database Connection Pool Exhaustion",
            symptoms=[
                "API requests timeout with 'Unable to acquire connection' errors",
                "Database connection count at maximum (e.g., 100/100 in use)",
                "API error rate spikes to >50%",
                "Prometheus metric pg_stat_activity > max_connections",
            ],
            diagnosis_steps=[
                "Check current connections: `SELECT count(*) FROM pg_stat_activity;`",
                "Find long-running queries: `SELECT * FROM pg_stat_activity WHERE query != 'IDLE' ORDER BY query_start;`",
                "Check API logs for 'connection pool' or 'timeout' keywords",
                "Look at Grafana: Database → Connections panel",
                "Review slow query log: `SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;`",
            ],
            mitigation_strategies=[
                "Kill idle connections: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < NOW() - INTERVAL '10 minutes';`",
                "Kill stuck query: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query LIKE '%VACUUM%';`",
                "Increase connection pool size (requires restart): edit connection pool config",
                "Scale API instances to reduce per-instance load",
                "Enable connection pooling middleware (pgBouncer) if not already enabled",
                "Disable non-critical background jobs temporarily",
            ],
            escalation_criteria=(
                "Escalate to database team if: "
                "(1) killing idle connections doesn't help within 5 min, "
                "(2) stuck query is from maintenance task with legitimate reason to run, "
                "(3) issue recurs multiple times per week, "
                "(4) requires schema changes to reduce query load"
            ),
            reference_incidents=[
                "INC-2026-001: Database Latency Spike Causes API Connection Pool Exhaustion",
            ]
        ),

        RunbookEntry(
            issue_name="High Memory Usage in API Container",
            symptoms=[
                "Container killed with OOMKilled status",
                "Prometheus memory_usage_bytes near container limit",
                "API becomes unresponsive",
                "Docker logs show 'Killed' without error message",
            ],
            diagnosis_steps=[
                "Check container memory limit: `docker inspect <container-id> | grep Memory`",
                "Check actual memory usage: `docker stats <container-id>`",
                "Look for memory leaks in logs: search for 'leaked' or 'growing' in app logs",
                "Check if recent deployment increased memory footprint",
                "Look at Grafana Memory panel for growth pattern (gradual vs sudden)",
                "Check if cache grew unbounded: `SELECT SIZE() FROM cache_table;`",
            ],
            mitigation_strategies=[
                "Increase container memory limit (requires restart)",
                "Restart the container to reset memory (temporary fix)",
                "Disable memory-intensive features temporarily (caching, batch processing)",
                "Scale horizontally: add more instances with lower memory requirements",
                "Enable garbage collection in logs to verify cleanup is happening",
            ],
            escalation_criteria=(
                "Escalate to engineering team if: "
                "(1) memory grows unbounded (likely memory leak), "
                "(2) issue appears after recent code change, "
                "(3) increasing limit doesn't solve recurring OOMKill, "
                "(4) memory footprint is >50% higher than baseline"
            ),
            reference_incidents=[
                "INC-2026-003: Memory Leak in Session Cache",
            ]
        ),

        RunbookEntry(
            issue_name="RAG Retrieval Returning Stale or Wrong Documents",
            symptoms=[
                "User reports AI assistant gives outdated information",
                "Evaluation tests fail: retrieval accuracy drops",
                "Retrieved documents timestamp older than expected",
                "Tempo traces show retrieval latency normal but quality degraded",
            ],
            diagnosis_steps=[
                "Check embedding index timestamp: `SELECT created_at FROM embedding_index_metadata ORDER BY created_at DESC LIMIT 1;`",
                "Compare index timestamp with knowledge base update timestamp",
                "Sample 10 recent retrieval traces from Tempo; check document versions",
                "Run evaluation suite: `python -m app.evaluate --num_queries=100`",
                "Check if knowledge base webhook firing: look for webhook delivery logs in GitHub",
                "Verify embedding model version hasn't changed: `curl /api/config | jq .embedding_model`",
            ],
            mitigation_strategies=[
                "Trigger immediate re-indexing: `python scripts/reindex_knowledge.py --force`",
                "Wait for re-indexing to complete (typically 2-5 minutes)",
                "Run evaluation to verify accuracy returned to baseline",
                "Monitor retrieval latency during re-indexing (should stay <200ms)",
                "As temporary workaround: disable retrieval feature and use only semantic search",
            ],
            escalation_criteria=(
                "Escalate to AI/ML team if: "
                "(1) re-indexing fails, "
                "(2) accuracy doesn't improve after re-index, "
                "(3) issue recurs >2 times per week (indicates automation failure), "
                "(4) embedding model version mismatch detected"
            ),
            reference_incidents=[
                "INC-2026-005: RAG Retrieval Returning Stale Knowledge Base",
            ]
        ),

        RunbookEntry(
            issue_name="AI Model Timeout (LLM Generation Taking Too Long)",
            symptoms=[
                "API /api/chat requests timeout after 30 seconds",
                "LLM response time consistently >30 seconds",
                "Trace shows 'waiting for model response' taking entire duration",
                "Error: 'Model API timeout' in logs",
            ],
            diagnosis_steps=[
                "Check LLM provider status: curl https://status.openai.com or equivalent",
                "Look at Tempo traces: which stage is slow? Prompt building vs actual generation?",
                "Check input complexity: prompt length, context window size",
                "Verify model version hasn't changed: `SELECT model_version FROM model_config;`",
                "Check rate limiting: are we hitting provider's rate limit?",
                "Review recent code changes: did we increase prompt length or context window?",
            ],
            mitigation_strategies=[
                "Increase API timeout temporarily (if acceptable for SLA): increase from 30s to 60s",
                "Reduce context window size: limit retrieval results from 10 to 5 documents",
                "Simplify prompt: remove examples, reduce formatting instructions",
                "Switch to faster model (lower quality but lower latency): e.g., GPT-4o mini instead of GPT-4",
                "Queue requests: implement request queuing with background processing",
                "Enable streaming: return partial responses to user while generating",
            ],
            escalation_criteria=(
                "Escalate to product/engineering if: "
                "(1) provider (OpenAI/Anthropic) is down, "
                "(2) model quality drops with timeout increase, "
                "(3) issue is due to recent feature that increases context, "
                "(4) need to redesign how context is provided"
            ),
            reference_incidents=[
                "INC-2026-002: Model Timeout During Context Window Expansion",
            ]
        ),
    ]

    return entries


if __name__ == "__main__":
    entries = create_example_runbook_entries()
    markdown = generate_runbook_markdown(entries)
    print(markdown)
