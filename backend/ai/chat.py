SYSTEM_PROMPT_TEMPLATE = (
    "You are a consulting assistant answering questions about a client "
    "engagement using ONLY the excerpts provided below. If the answer "
    "isn't in these excerpts, say you don't have that information in "
    "the uploaded documents — do not use outside knowledge or guess.\n\n"
    "Relevant excerpts:\n{context}"
)


def build_context(collection, question: str, n_results: int = 4) -> tuple[str, list[str]]:
    results = collection.query(query_texts=[question], n_results=n_results)
    parts = []
    sources = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        parts.append(f"[Source: {meta.get('source')}]\n{doc}")
        sources.append(meta.get("source"))
    return "\n\n---\n\n".join(parts), sources


def answer_question(anthropic_client, collection, messages: list[dict]) -> tuple[str, list[str]]:
    # Retrieval is based on the latest question only, not the whole
    # conversation — simple and works well for a first version. Memory
    # of earlier turns comes entirely from `messages` being passed through
    # to Claude, not from anything we do here.
    question = messages[-1]["content"]
    context, sources = build_context(collection, question)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=system_prompt,
        messages=messages,
    )
    answer = response.content[0].text
    return answer, sources
