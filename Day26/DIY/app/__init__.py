"""
Day26 DIY - AI Alerting Triage System

This module implements the alerting triage logic described in Day26.
Signals are classified into three routes:
- pager: immediate on-call escalation for wide-impact failures
- evaluation_queue: quality/performance signals for batch analysis
- security_review: high-risk safety events for dedicated review
"""
