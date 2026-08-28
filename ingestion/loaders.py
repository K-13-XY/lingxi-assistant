"""文档加载器：按扩展名分派，统一返回 List[Document]

支持 txt | md | pdf | csv | xlsx
考勤等结构化表格数据会逐行转成自然语言句子再入库，检索效果才有保证。
"""
import csv
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from openpyxl import load_workbook

# 支持的扩展名 -> 加载函数
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".csv", ".xlsx"}

# 考勤表常用列名（兼容中英文/带不带括号的变体）
_COL_ALIASES = {
    "学号": ["学号", "student_id", "学号(student_id)", "ID"],
    "姓名": ["姓名", "name", "学生姓名"],
    "日期": ["日期", "date", "考勤日期"],
    "节次": ["节次", "period", "第几节", "上课节次"],
    "状态": ["状态", "status", "考勤状态", "出勤情况"],
}


def _pick(cols: list, *names: str) -> str | None:
    """在表头里按别名查找目标列"""
    for n in names:
        for c in cols:
            if str(c).strip().lstrip("·").lower() == n.lower():
                return c
    return None


def _read_text_with_fallback(path: Path) -> str:
    """读取文本，优先 utf-8，Windows 常见 gbk 编码回退"""
    for enc in ("utf-8", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法解码文件：{path.name}（尝试过 utf-8/gbk）")


def _load_text(path: Path) -> Document:
    return Document(page_content=_read_text_with_fallback(path), metadata={"source": path.name})


def _load_pdf(path: Path) -> List[Document]:
    loader = PyPDFLoader(str(path))
    docs = loader.load()
    for d in docs:
        d.metadata["source"] = path.name
    return docs


def _format_attendance_row(row: dict) -> str:
    """把一行考勤记录格式化转成自然语言句子"""
    sid = row.get("学号") or "未知学号"
    name = row.get("姓名") or ""
    date = row.get("日期") or ""
    period = row.get("节次") or ""
    status = row.get("状态") or "未记录"
    return f"{date} 第{period}节，学号{sid}({name})，考勤状态为：{status}"


def _load_csv(path: Path) -> List[Document]:
    lines: List[str] = []
    # utf-8-sig 兼容 BOM 文件（Excel/seed 脚本导出的常见形态）
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        if not cols:
            return []
        normalized = []
        for raw in reader:
            row = {}
            for std, aliases in _COL_ALIASES.items():
                col = _pick(cols, *aliases)
                if col is not None:
                    row[std] = raw[col]
            normalized.append(row)
        lines = [_format_attendance_row(r) for r in normalized if any(r.values())]
    return [Document(page_content="\n".join(lines), metadata={"source": path.name})]


def _load_xlsx(path: Path) -> List[Document]:
    wb = load_workbook(path, read_only=True, data_only=True)
    lines: List[str] = []
    for sheet in wb.worksheets:
        rows = sheet.iter_rows(values_only=True)
        header = next(rows, None)
        if header is None:
            continue
        cols = list(header)
        normalized = []
        for values in rows:
            raw = dict(zip(cols, values))
            row = {}
            for std, aliases in _COL_ALIASES.items():
                col = _pick(cols, *aliases)
                if col is not None:
                    row[std] = raw.get(col, "")
            normalized.append(row)
        lines += [
            _format_attendance_row(r)
            for r in normalized
            if any(v not in (None, "") for v in r.values())
        ]
    wb.close()
    return [Document(page_content="\n".join(lines), metadata={"source": path.name})]


def load_file(path: Path) -> List[Document]:
    """加载单个文件为 Document 列表（一个文件可能产出多条）"""
    path = Path(path)
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型：{ext}，支持 {sorted(SUPPORTED_EXTENSIONS)}")
    if ext in (".txt", ".md"):
        return [_load_text(path)]
    if ext == ".pdf":
        return _load_pdf(path)
    if ext == ".csv":
        return _load_csv(path)
    if ext == ".xlsx":
        return _load_xlsx(path)
    raise ValueError(f"不支持的文件类型：{ext}")
