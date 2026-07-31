from langchain_text_splitters import RecursiveCharacterTextSplitter

# 300/50 was deliberately tiny in the Colab demo so one short transcript
# would split into multiple visible chunks. Real documents (reports,
# transcripts) use a larger window — 800 characters (~150-200 tokens) is
# a common default: big enough to hold a full idea, small enough that
# each chunk's embedding stays focused on one topic.
splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_text(text: str) -> list[str]:
    return splitter.split_text(text)
