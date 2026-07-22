"""
企业智能知识库助手 - 终端交互模式
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
        category = source.get("metadata", {}).get("category", "未分类")
        score = source.get("score", 0)
        print(f"  [{i}] {category} (相关度: {score:.2%})")
        content = source.get("content", "")[:100]
        if content:
            print(f"      {content}...")


def print_tools(tools: list):
    """打印使用的工具"""
    if not tools:
        return

    tool_names = {
        "search_knowledge_base": "知识库搜索",
        "get_current_time": "时间查询",
        "calculator": "计算器",
        "explain_concept": "概念解释"
    }

    print("\n🔧 使用工具:", ", ".join([tool_names.get(t, t) for t in tools]))


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
    print(f"✅ 知识库加载完成!")
    print(f"   文档数量: {stats['document_count']}")
    print(f"   文本块数量: {stats['chunk_count']}")

    # 初始化记忆管理器
    memory = ConversationMemory(max_history=20)

    # 初始化Agent
    agent = Agent(config, rag_engine, memory)

    # 检查API密钥
    if not config.llm.api_key:
        print("\n⚠️  警告: 未设置MOONSHOT_API_KEY，LLM功能将不可用")
        print("   请在 .env 文件中配置 MOONSHOT_API_KEY")

    print("\n💡 输入问题开始对话，输入 'quit' 或 '退出' 结束")
    print("-" * 60)

    conversation_id = None

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
                print(f"\n📊 知识库统计:")
                print(f"   文档数量: {stats['document_count']}")
                print(f"   文本块数量: {stats['chunk_count']}")
                continue

            if user_input.lower() in ['help', '帮助']:
                print("\n📖 命令说明:")
                print("   new/clear/新对话  - 开始新对话")
                print("   stats/统计        - 查看知识库统计")
                print("   help/帮助         - 显示帮助信息")
                print("   quit/exit/退出    - 退出程序")
                continue

            # 发送消息
            result = await agent.chat(user_input, conversation_id)

            # 更新会话ID
            conversation_id = result["conversation_id"]

            # 显示查询类型
            route_type = result.get("route_type", "general")
            route_names = {"list": "列表查询", "detail": "详细查询", "general": "一般查询"}
            print(f"\n🎯 查询类型: {route_names.get(route_type, route_type)}")

            # 打印回答
            print(f"\n💬 回答:\n{result['answer']}")

            # 打印来源（简化格式）
            sources = result.get("sources", [])
            if sources:
                print("\n📎 来源:")
                for i, src in enumerate(sources[:3], 1):
                    metadata = src.get("metadata", {})
                    doc_name = metadata.get("document_name", "未知")
                    category = metadata.get("category", "")
                    score = src.get("score", 0)
                    print(f"  [{i}] {doc_name} ({category}) - {score:.1%}")

        except KeyboardInterrupt:
            print("\n\n👋 感谢使用，再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            continue


if __name__ == "__main__":
    asyncio.run(main())
