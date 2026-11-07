from app.documents import Document, annual_leave_document, remote_work_document


def retrieve_context(
    question: str,
) -> list[Document]:
    q = question.lower()

    if "remote" in q:
        return [remote_work_document]

    if "leave" in q:
        return [annual_leave_document]

    return []
