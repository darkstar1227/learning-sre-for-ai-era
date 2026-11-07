from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    document_id: str
    title: str
    content: str


remote_work_document = Document(
    document_id="company-policy-remote-work",
    title="Remote Work",
    content=(
        "Full-time employees may work remotely up to two days per week. "
        "Remote work requires manager approval. "
        "Employees must be available during core hours from 10:00 to 16:00."
    ),
)

annual_leave_document = Document(
    document_id="company-policy-annual-leave",
    title="Annual Leave",
    content=(
        "Employees receive 12 days of annual leave after completing one year. "
        "Leave requests should be submitted at least three business days in advance."
    ),
)
