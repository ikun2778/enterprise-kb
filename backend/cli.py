"""
企业智能知识库助手 - 终端交互模式
支持流式输出、查询路由、多轮对话
"""

import sys
import asyncio
from pathlib import Path

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent))

from app.config import config, ensure_dirs, KNOWLEDGE_BASE_DIR
from app.core.rag_engine import RAGEngine
from app.core.agent import Agent
from app.core.memory import ConversationMemory


def print_banner():
    """打印欢迎横幅"""
    print("=" * 60)
    print("📚 企业智能知识库助手 - 终端问答模式")
    print("=" * 60)
    print(f"LLM模型: {config.llm.model}")
    print(f"Embedding模型: {config.embedding.model_name}")
    print("=" * 60)


def print_sources(sources: list):
    """打印来源文档"""
    if not sources:
        return

    print("\n📎 来源文档:")
    for i, source in enumerate(sources, 1):
        metadata = source.get("metadata", {})
        category = metadata.get("category", "未分类")
        doc_name = metadata.get("document_name", "未知")
        score = source.get("score", 0)
        print(f"  [{i}] {doc_name} ({category}) - 相关度: {score:.2%}")


def print_route_info(route_type: str):
    """打印路由类型信息"""
    route_names = {
        "list": "📋 列表查询",
        "detail": "📖 详细查询",
        "general": "💬 一般查询"
    }
    print(f"\n🎯 查询类型: {route_names.get(route_type, route_type)}")


def print_stats(stats: dict):
    """打印统计信息"""
    print("\n📊 知识库统计:")
    print(f"   文档数量: {stats['document_count']}")
    print(f"   文本块数量: {stats['chunk_count']}")
    print(f"   向量索引: {'✅ 就绪' if stats['vector_store_ready'] else '❌ 未就绪'}")
    print(f"   BM25索引: {'✅ 就绪' if stats['bm25_ready'] else '❌ 未就绪'}")

    categories = stats.get('categories', {})
    if categories:
        print("\n📂 分类分布:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"   {cat}: {count} 篇")


def process_stream(answer_generator):
    """处理流式输出"""
    for chunk in answer_generator:
        print(chunk, end="", flush=True)
    print()  # 换行


async def main():
    """主函数"""
    print_banner()

    # 确保目录存在
    ensure_dirs()

    # 初始化RAG引擎
    print("\n⏳ 正在初始化RAG引擎...")
    rag_engine = RAGEngine(config)

    # 加载知识库
    data_path = str(KNOWLEDGE_BASE_DIR)
    print(f"📂 加载知识库: {data_path}")
    rag_engine.initialize(data_path)

    # 打印统计信息
    stats = rag_engine.get_stats()
    print_stats(stats)

    # 初始化记忆管理器
    memory = ConversationMemory(max_history=20)

    # 初始化Agent
    agent = Agent(config, rag_engine, memory)

    # 检查API密钥
    if not config.llm.api_key:
        print("\n⚠️  警告: 未设置MOONSHOT_API_KEY，LLM功能将不可用")
        print("   请在 .env 文件中配置 MOONSHOT_API_KEY")

    print("\n💡 输入问题开始对话")
    print("   命令: new(新对话) | stats(统计) | stream(切换流式) | help(帮助) | quit(退出)")
    print("-" * 60)

    conversation_id = None
    use_stream = False  # 是否使用流式输出

    while True:
        try:
            # 获取用户输入
            user_input = input("\n❓ 您的问题: ").strip()

            # 检查退出命令
            if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                print("\n👋 感谢使用，再见！")
                break

            # 跳过空输入
            if not user_input:
                continue

            # 处理特殊命令
            if user_input.lower() in ['new', '新对话', 'clear']:
                conversation_id = None
                print("🆕 已开始新对话")
                continue

            if user_input.lower() in ['stats', '统计']:
                stats = rag_engine.get_stats()
                print_stats(stats)
                continue

            if user_input.lower() in ['stream', '流式']:
                use_stream = not use_stream
                print(f"🔄 流式输出: {'开启' if use_stream else '关闭'}")
                continue

            if user_input.lower() in ['help', '帮助']:
                print("\n📖 命令说明:")
                print("   new/clear/新对话    - 开始新对话")
                print("   stats/统计          - 查看知识库统计")
                print("   stream/流式         - 切换流式输出模式")
                print("   help/帮助           - 显示帮助信息")
                print("   quit/exit/退出      - 退出程序")
                print("\n💡 查询类型说明:")
                print("   list   - 列表查询，返回相关文档名称")
                print("   detail - 详细查询，返回分步解释")
                print("   general- 一般查询，返回基础回答")
                continue

            # 发送消息
            print("\n⏳ 思考中...")
            result = await agent.chat(user_input, conversation_id, stream=use_stream)

            # 更新会话ID
            conversation_id = result["conversation_id"]

            # 打印路由信息
            print_route_info(result.get("route_type", "general"))

            # 打印回答
            if result.get("stream"):
                # 流式输出
                print("\n💬 回答:")
                process_stream(result["answer_generator"])
            else:
                # 普通输出
                print("\n💬 回答:")
                print(result["answer"])

            # 打印来源
            print_sources(result.get("sources", []))

        except KeyboardInterrupt:
            print("\n\n👋 感谢使用，再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            continue


if __name__ == "__main__":
    asyncio.run(main())
