import json
import urllib.request

# 1. 文档列表
print("=== GET /api/documents ===")
with urllib.request.urlopen("http://localhost:8000/api/documents", timeout=30) as resp:
    d = json.loads(resp.read().decode("utf-8"))
    docs = d.get("documents", [])
    print("文档数量:", len(docs))
    for x in docs:
        print("   ", x.get("doc_id"), x.get("filename"), x.get("chunk_count"))

# 2. 流式检索
print()
print("=== POST /api/chat/stream (奖学金) ===")
body = json.dumps({"question": "奖学金评定标准是什么？"}, ensure_ascii=False).encode("utf-8")
req = urllib.request.Request(
    "http://localhost:8000/api/chat/stream",
    data=body,
    headers={"Content-Type": "application/json; charset=utf-8"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=90) as resp:
        print("status:", resp.status, "content-type:", resp.headers.get("Content-Type"))
        raw = resp.read().decode("utf-8")
    print("流式返回长度:", len(raw))
    print("是否含 SOURCES 标记:", "===SOURCES===" in raw)
    idx = raw.find("===SOURCES===")
    if idx >= 0:
        print("--- 答案部分 ---")
        print(raw[:idx].strip()[:200])
        print("--- 来源 JSON ---")
        print(raw[idx:].strip()[:300])
    else:
        print("--- 全文 ---")
        print(raw[:400])
except Exception as e:
    print("流式请求失败:", repr(e))
