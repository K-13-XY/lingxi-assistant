"""文档切分：中文场景的 RecursiveCharacterTextSplitter（md 按标题切分）"""
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

import settings as config


def get_splitter() -> RecursiveCharacterTextSplitter:
    # 中文标点（句号/感叹号/问号/分号/逗号）排在英文空格之前
    # 避免英文优先切分把中文句子从中间劈开
    return RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        length_function=len,
    )


_MD_HEADER_SPLITTER = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "章"), ("##", "节")]
)


def split_documents(docs: list[Document], doc_id: str) -> list[Document]:
    """切分文档并补全 metadata（source 文件名 + doc_id + chunk_index）

    markdown 文档按标题（#/##）切分，保证每个块主题聚焦，检索更准；
    其余格式用 RecursiveCharacterTextSplitter。
    """
    chunks: list[Document] = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        if source.lower().endswith(".md"):
            pieces = _MD_HEADER_SPLITTER.split_text(doc.page_content)
            # MarkdownHeaderTextSplitter 产出无 content 的空块时跳过
            pieces = [p for p in pieces if p.page_content.strip()]
            # 无标题结构时回退通用切分
            if not pieces:
                pieces = get_splitter().split_documents([doc])
        else:
            pieces = get_splitter().split_documents([doc])
        for i, chunk in enumerate(pieces):
            chunk.metadata = {
                "source": source,
                "doc_id": doc_id,
                "chunk_index": i,
            }
            chunks.append(chunk)
    return chunks
