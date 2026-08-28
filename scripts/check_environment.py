"""环境自检脚本：核对依赖版本、Embedding 连通性、向量维度、DeepSeek Key 配置。

用法：python scripts/check_environment.py
"""
import sys
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Windows 控制台默认 GBK，强制 UTF-8 避免中文输出乱码
sys.stdout.reconfigure(encoding="utf-8")

import settings as config
from core.embeddings import probe_embeddings_dim

OK = "\033[92m[OK]\033[0m"
WARN = "\033[93m[WARN]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"


def main() -> None:
    print("=" * 56)
    print(" 灵犀智能助手 —— 环境自检")
    print("=" * 56)

    # 1. Python 与依赖版本
    print(f"\n[Python] {sys.version.split()[0]}")
    try:
        import langchain, langchain_milvus, pymilvus, milvus_lite, fastapi  # noqa: F401
        import langchain_openai, langchain_community  # noqa: F401

        print(f"{OK} langchain=={langchain.__version__}")
        print(f"{OK} langchain-milvus=={version('langchain-milvus')}")
        print(f"{OK} pymilvus=={version('pymilvus')}")
        print(f"{OK} milvus-lite=={version('milvus-lite')}")
        print(f"{OK} fastapi=={version('fastapi')}")
    except ImportError as e:
        print(f"{FAIL} 依赖缺失：{e}\n    请先执行: pip install -r requirements.txt")
        return

    # 2. Embedding（阿里云百炼 DashScope）
    print("\n[Embedding]")
    if not config.EMBEDDING_API_KEY:
        print(f"{FAIL} 未配置 EMBEDDING_API_KEY，请编辑 .env 填入阿里云百炼的 API Key")
    else:
        try:
            dim = probe_embeddings_dim()
            if dim == config.EMBEDDING_DIM:
                print(f"{OK} {config.EMBEDDING_MODEL} 连通，输出维度 = {dim}（配置一致）")
            else:
                print(f"{WARN} 维度 {dim} 与配置 {config.EMBEDDING_DIM} 不一致，请更新 .env 的 EMBEDDING_DIM")
        except Exception as e:
            print(f"{FAIL} DashScope 不可用：{e}")
            print("    请检查 EMBEDDING_API_KEY 是否正确、百炼服务是否已开通")

    # 3. DeepSeek
    print("\n[DeepSeek]")
    if config.DEEPSEEK_API_KEY and config.DEEPSEEK_API_KEY != "sk-xxxx":
        print(f"{OK} API Key 已配置（{config.DEEPSEEK_MODEL} @ {config.DEEPSEEK_BASE_URL}）")
    else:
        print(f"{FAIL} 未配置 DEEPSEEK_API_KEY，请编辑 .env 填入 DeepSeek 的 API Key")

    # 4. 数据目录
    print("\n[数据目录]")
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"{OK} {config.DATA_DIR}")

    print("\n" + "=" * 56)


if __name__ == "__main__":
    main()
