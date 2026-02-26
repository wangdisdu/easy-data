"""
TextToSqlAgent - 文本转SQL智能体
使用LangGraph实现，将自然语言问题转换为SQL查询语句
"""

import json
from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.agent.agent_utils import setup_langsmith_tracing
from app.agent.base_agent import BaseAgent
from app.agent.text_to_sql_agent_prompts import INTENT_ANALYSIS_PROMPT, TEXT_TO_SQL_BEST_PRACTICES
from app.core.logging import get_logger
from app.dao.database import SessionLocal
from app.dao.models import TbDataModel
from app.tool import tool_execute_sql_data_source, tool_get_data_models_semantic

logger = get_logger("text_to_sql_agent")

# 在模块加载时设置 LangSmith 追踪
setup_langsmith_tracing()

# 最大重试次数常量（最多重试5次）
MAX_RETRY_COUNT = 5


class TextToSqlAgentState(TypedDict):
    """文本转SQL Agent状态定义"""

    messages: Annotated[list[BaseMessage], add_messages]  # 所有历史消息
    user_input: HumanMessage  # 用户输入
    session_id: str
    user_id: Optional[int]
    retry_count: int  # SQL错误重试次数
    semantic_prompt: Optional[str]  # 基于选中模型semantic构建的提示词


class TextToSqlAgent(BaseAgent):
    """文本转SQL智能体，使用LangGraph实现"""

    def __init__(self, user_id: Optional[int] = None):
        super().__init__(user_id=user_id)

        # 在初始化时加载所有模型的summary信息，构建默认系统提示词
        self.summary_prompt = self._build_summary_prompt()

        # 定义工具
        # 第一步：意图分析工具（获取semantic）
        self.intent_analysis_tools = [tool_get_data_models_semantic]
        # 第三步：SQL生成工具（执行SQL）
        self.sql_generation_tools = [tool_execute_sql_data_source]

        # 绑定工具到LLM
        self.llm_intent_analysis = self.llm.bind_tools(self.intent_analysis_tools)
        self.llm_sql_generation = self.llm.bind_tools(self.sql_generation_tools)

        # 创建工具节点
        self.intent_analysis_tool_node = ToolNode(self.intent_analysis_tools)
        self.sql_generation_tool_node = ToolNode(self.sql_generation_tools)

        # 构建LangGraph工作流
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """
        构建LangGraph工作流

        工作流包含以下节点:
        1. intent_analysis: 分析用户意图，判断是否能解决
        2. intent_analysis_tools: 执行获取semantic工具
        3. get_semantic: 获取选中模型的semantic信息
        4. sql_generation: 基于semantic生成SQL
        5. sql_generation_tools: 执行SQL
        6. counter_retry: 更新重试次数

        Returns:
            StateGraph: 编译后的工作流图
        """
        workflow = StateGraph(TextToSqlAgentState)

        # 添加节点
        workflow.add_node("intent_analysis", self._intent_analysis_node)
        workflow.add_node("intent_analysis_tools", self.intent_analysis_tool_node)
        workflow.add_node("extract_semantic", self._extract_semantic_node)
        workflow.add_node("sql_generation", self._sql_generation_node)
        workflow.add_node("sql_generation_tools", self.sql_generation_tool_node)
        workflow.add_node("counter_retry", self._update_retry_count_node)

        # 设置入口点
        workflow.set_entry_point("intent_analysis")

        # 意图分析后，判断是否需要继续执行工具
        workflow.add_conditional_edges(
            "intent_analysis",
            self._after_intent_analysis,
            {"continue": "intent_analysis_tools", "end": END},
        )

        # 意图分析工具执行后，判断是否已获取到semantic
        workflow.add_conditional_edges(
            "intent_analysis_tools",
            self._after_intent_analysis_tools,
            {"continue": "intent_analysis", "semantic": "extract_semantic", "end": END},
        )

        # 获取semantic后，进入SQL生成阶段
        workflow.add_edge("extract_semantic", "sql_generation")

        # SQL生成后，判断是否需要继续执行工具
        workflow.add_conditional_edges(
            "sql_generation",
            self._after_sql_generation,
            {"continue": "sql_generation_tools", "end": END},
        )

        # SQL生成工具执行后，更新重试次数或返回SQL生成
        workflow.add_conditional_edges(
            "sql_generation_tools",
            self._after_sql_generation_tools,
            {"retry": "counter_retry", "continue": "sql_generation", "end": END},
        )

        # 更新重试次数后，返回SQL生成
        workflow.add_edge("counter_retry", "sql_generation")

        # 编译工作流
        graph = workflow.compile()
        return graph

    async def _intent_analysis_node(self, state: TextToSqlAgentState) -> TextToSqlAgentState:
        """
        第一步：意图分析节点
        根据用户问题和模型summary，分析用户问题涉及到了哪些模型的数据

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        try:
            user_input = state.get("user_input")
            his_messages = state.get("messages", [])

            # 构建完整的系统提示词（意图分析提示词 + summary背景知识）
            system_prompt = f"""{INTENT_ANALYSIS_PROMPT}

{self.summary_prompt}
"""

            # 构建消息列表（使用完整的系统提示词 + 历史消息）
            messages = [
                SystemMessage(content=system_prompt),
                user_input,
                *his_messages,
            ]

            logger.info(f"[INTENT-ANALYSIS] [LLM-INPUT] 用户问题: {user_input.content[:100]}...")

            # 使用意图分析LLM
            response = await self.llm_intent_analysis.ainvoke(messages)

            logger.info("[INTENT-ANALYSIS] [LLM-OUTPUT] 意图分析响应")

            return {**state, "messages": [*his_messages, response]}
        except Exception as e:
            error_msg = f"意图分析失败: {e!s}"
            logger.exception("[INTENT-ANALYSIS] [ERROR] 意图分析失败")
            return {
                **state,
                "messages": [
                    *state.get("messages", []),
                    AIMessage(content=error_msg),
                ],
            }

    async def _extract_semantic_node(self, state: TextToSqlAgentState) -> TextToSqlAgentState:
        """
        第二步：获取语义信息节点
        从工具结果中提取模型ID，构建semantic提示词

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        try:
            messages = state.get("messages", [])

            # 查找最后的tool_get_data_models_semantic工具结果
            semantic_content = None

            for msg in reversed(messages):
                if hasattr(msg, "name") and msg.name == "tool_get_data_models_semantic":
                    semantic_content = msg.content
                    break

            if not semantic_content:
                error_msg = "未找到模型语义信息，请先选择模型"
                logger.error("[GET-SEMANTIC] [ERROR] 未找到模型语义信息")
                return {
                    **state,
                    "messages": [
                        *state.get("messages", []),
                        AIMessage(content=error_msg),
                    ],
                }

            try:
                # 解析语义信息
                models_data = json.loads(semantic_content)

                # 构建semantic提示词
                semantic_prompt = self._build_semantic_prompt(models_data)

                logger.info(f"[GET-SEMANTIC] [SUCCESS] 获取到 {len(models_data)} 个模型的语义信息")

                return {
                    **state,
                    "semantic_prompt": semantic_prompt,
                }
            except json.JSONDecodeError:
                error_msg = f"解析模型语义信息失败：{semantic_content}"
                logger.exception(f"[GET-SEMANTIC] [ERROR] {error_msg}")
                return {
                    **state,
                    "messages": [
                        *state.get("messages", []),
                        AIMessage(content=error_msg),
                    ],
                }
        except Exception as e:
            error_msg = f"获取语义信息失败: {e!s}"
            logger.exception("[GET-SEMANTIC] [ERROR] 获取语义信息失败")
            return {
                **state,
                "messages": [
                    *state.get("messages", []),
                    AIMessage(content=error_msg),
                ],
            }

    async def _sql_generation_node(self, state: TextToSqlAgentState) -> TextToSqlAgentState:
        """
        第三步：SQL生成节点
        根据用户问题和选中模型的semantic生成SQL

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        try:
            user_input = state.get("user_input")
            retry_count = state.get("retry_count", 0)
            semantic_prompt = state.get("semantic_prompt")

            # 检查是否有semantic提示词
            if not semantic_prompt:
                error_msg = "未找到模型语义信息，无法生成SQL"
                logger.error("[SQL-GENERATION] [ERROR] 未找到模型语义信息")
                return {
                    **state,
                    "messages": [
                        *state.get("messages", []),
                        AIMessage(content=error_msg),
                    ],
                }

            # 检查重试次数，避免无限循环
            if retry_count >= MAX_RETRY_COUNT:
                error_msg = (
                    f"SQL执行连续{MAX_RETRY_COUNT}次失败，已停止重试。请检查SQL语法或联系管理员。"
                )
                logger.warning(f"[SQL-GENERATION] [RETRY-LIMIT] 达到最大重试次数: {retry_count}")
                return {
                    **state,
                    "messages": [*state.get("messages", []), AIMessage(content=error_msg)],
                }

            # 获取历史消息
            his_messages = state.get("messages", [])

            # 构建完整的系统提示词（最佳实践 + semantic背景知识）
            system_prompt = f"""{TEXT_TO_SQL_BEST_PRACTICES}

{semantic_prompt}
"""

            # 构建消息列表（使用完整的系统提示词 + 历史消息）
            messages = [SystemMessage(content=system_prompt), user_input, *his_messages]

            logger.info(
                f"[SQL-GENERATION] [LLM-INPUT] 用户问题: {user_input.content[:100]}..., 重试次数: {retry_count}"
            )

            # 使用SQL生成LLM
            response = await self.llm_sql_generation.ainvoke(messages)

            sql_content = response.content if response.content else ""
            logger.info(f"[SQL-GENERATION] [LLM-OUTPUT] 生成的SQL长度: {len(sql_content)} 字符")

            return {**state, "messages": [*his_messages, response], "retry_count": retry_count}
        except Exception as e:
            error_msg = f"生成SQL失败: {e!s}"
            logger.exception("[SQL-GENERATION] [ERROR] 生成SQL失败")
            return {
                **state,
                "messages": [
                    *state.get("messages", []),
                    AIMessage(content=error_msg),
                ],
            }

    def _after_intent_analysis(self, state: TextToSqlAgentState) -> str:
        """意图分析后的判断逻辑"""
        messages = state.get("messages", [])
        if not messages:
            return "end"

        last_message = messages[-1]

        # 如果最后一条消息包含工具调用，继续执行工具
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"

        # 如果没有工具调用，说明LLM判断不能解决，直接结束
        return "end"

    def _after_intent_analysis_tools(self, state: TextToSqlAgentState) -> str:
        """意图分析工具执行后的判断逻辑"""
        messages = state.get("messages", [])
        if not messages:
            return "end"

        # 查找最后的tool_get_data_models_semantic工具结果
        for msg in reversed(messages):
            if hasattr(msg, "name") and msg.name == "tool_get_data_models_semantic":
                # 检查是否是错误信息（不是JSON格式）
                content = msg.content
                if content.strip().startswith("[") or content.strip().startswith("{"):
                    # 是JSON格式，说明成功获取到语义信息
                    return "semantic"
                else:
                    # 是错误信息
                    return "end"

        # 检查是否还有工具调用需要执行
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"

        return "end"

    def _after_sql_generation(self, state: TextToSqlAgentState) -> str:
        """SQL生成后的判断逻辑"""
        messages = state.get("messages", [])
        if not messages:
            return "end"

        last_message = messages[-1]

        # 如果最后一条消息包含工具调用，继续执行工具
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        else:
            return "end"

    def _after_sql_generation_tools(self, state: TextToSqlAgentState) -> str:
        """SQL生成工具执行后的判断逻辑"""
        messages = state.get("messages", [])
        if not messages:
            return "end"

        # 查找最后的tool_execute_sql_data_source工具结果
        last_tool_message = None
        for msg in reversed(messages):
            if hasattr(msg, "name") and msg.name == "tool_execute_sql_data_source":
                last_tool_message = msg
                break

        if not last_tool_message:
            return "end"

        # 检查是否有错误需要重试
        if last_tool_message and hasattr(last_tool_message, "content"):
            content = last_tool_message.content
            # 判断是否是错误信息（不是JSON数组格式）
            if not (content.strip().startswith("[") or content.strip().startswith("{")):
                # 是错误信息，需要重试
                retry_count = state.get("retry_count", 0)
                if retry_count < MAX_RETRY_COUNT:
                    logger.info("[AFTER-SQL-TOOLS] 检测到SQL错误，准备重试")
                    return "retry"
                else:
                    logger.warning("[AFTER-SQL-TOOLS] 达到最大重试次数，停止重试")
                    return "end"

        # 检查LLM是否还需要继续处理（可能还有工具调用）
        last_llm_message = None
        for msg in reversed(messages):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                last_llm_message = msg
                break

        # 如果LLM还有工具调用，继续处理
        if last_llm_message and last_llm_message.tool_calls:
            return "continue"

        return "end"

    def _update_retry_count_node(self, state: TextToSqlAgentState) -> TextToSqlAgentState:
        """
        更新重试次数节点:检查工具执行结果，如果是错误则增加重试次数

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        messages = state.get("messages", [])
        retry_count = state.get("retry_count", 0)

        # 检查最后一条消息是否是工具执行结果
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, "content") and last_message.content:
                content = last_message.content
                # 判断是否是错误信息（不是JSON数组格式）
                if not (content.strip().startswith("[") or content.strip().startswith("{")):
                    # 是错误信息，增加重试次数
                    new_retry_count = retry_count + 1
                    logger.info(f"[UPDATE-RETRY-COUNT] SQL执行失败，重试次数: {new_retry_count}")
                    return {**state, "retry_count": new_retry_count}

        # 不是错误或没有消息，重置重试次数
        return {**state, "retry_count": 0}

    def _build_summary_prompt(self) -> str:
        """
        在初始化时构建所有模型的summary提示词

        Returns:
            summary提示词
        """
        db = SessionLocal()
        try:
            # 获取所有数据模型（只获取ds_id不为空且有summary的模型）
            data_models = (
                db.query(TbDataModel)
                .filter(TbDataModel.ds_id.isnot(None))
                .filter(TbDataModel.summary.isnot(None))
                .all()
            )

            if not data_models:
                summary_knowledge = "## 数据模型摘要信息\n\n当前没有可用的数据模型摘要信息。"
            else:
                summary_knowledge = "## 数据模型摘要信息\n\n"
                summary_knowledge += "以下是系统中所有可用的数据模型摘要信息，请根据这些信息理解表的基本含义，判断是否能解决用户问题。\n\n"

                for model in data_models:
                    if not model.summary:
                        continue

                    summary_knowledge += f"### 模型ID: {model.id}\n"
                    summary_knowledge += f"- **模型名称**: {model.name}\n"
                    summary_knowledge += f"- **摘要说明**:\n {model.summary}\n\n"

            logger.info(f"[BUILD-SUMMARY-PROMPT] 加载了 {len(data_models)} 个模型的摘要信息")

            return summary_knowledge
        except Exception:
            logger.exception("[BUILD-SUMMARY-PROMPT] [ERROR] 构建summary提示词失败")
            return "## 数据模型摘要信息\n\n构建摘要提示词失败。"
        finally:
            db.close()

    def _build_semantic_prompt(self, models_data: list[dict]) -> str:
        """
        根据选中的模型数据构建semantic提示词

        Args:
            models_data: 模型数据列表，每个元素包含id、code、name、platform、type、ds_id、ds_code、semantic等字段

        Returns:
            semantic提示词
        """
        try:
            if not models_data:
                return "## 数据模型背景知识\n\n当前没有选中的数据模型。"

            background_knowledge = "## 数据模型背景知识\n\n"
            background_knowledge += "以下是根据用户问题选择的相关数据模型及详细说明，请根据这些信息理解表结构、字段含义和业务关系，生成准确的SQL查询。\n\n"

            for model in models_data:
                if model.get("semantic"):
                    background_knowledge += f"# 模型:{model.get('name', 'N/A')}\n"
                    background_knowledge += (
                        f"- **平台（platform）**：{model.get('platform', 'N/A')}\n"
                    )
                    background_knowledge += f"- **类型（type）**：{model.get('type', 'N/A')}\n"
                    background_knowledge += (
                        f"- **数据源编码（ds_id_or_code）**：{model.get('ds_code', 'N/A')}\n"
                    )
                    background_knowledge += f"{model.get('semantic', '')}\n\n"

            logger.info(f"[BUILD-SEMANTIC-PROMPT] 构建了 {len(models_data)} 个模型的语义提示词")

            return background_knowledge
        except Exception:
            logger.exception("[BUILD-SEMANTIC-PROMPT] [ERROR] 构建semantic提示词失败")
            return "## 数据模型背景知识\n\n构建语义提示词失败。"

    def _build_initial_state(self, session_id: str, message: str) -> dict[str, Any]:
        """构建初始状态

        Args:
            session_id: 会话ID
            message: 用户消息

        Returns:
            初始状态字典
        """
        human_message = HumanMessage(content=message)
        return {
            "messages": [],
            "user_input": human_message,
            "session_id": session_id,
            "user_id": self.user_id,
            "retry_count": 0,
            "semantic_prompt": None,
        }
