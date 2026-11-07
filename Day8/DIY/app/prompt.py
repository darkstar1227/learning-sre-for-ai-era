from app.documents import Document


PROMPT_CONTRACT = """
Answer only from the supplied policy documents.
If the documents do not contain the answer, say that the information is unavailable.
For every policy claim, cite the supporting document ID.
Do not infer exceptions or invent company rules.
""".strip()


def build_prompt(
    question: str,
    documents: list[Document],
) -> str:
    if not documents:
        context = "(no documents retrieved)"
    else:
        context = "\n\n".join(
            f"[{document.document_id}]\n{document.content}"
            for document in documents
        )

    return f"""
{PROMPT_CONTRACT}

Retrieved documents:
{context}

User question:
{question}
""".strip()
