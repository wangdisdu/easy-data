"""
数据库模型定义
"""

from sqlalchemy import BigInteger, Column, Integer, String, Text

from app.dao.database import Base


class BaseModel(Base):
    """基础模型，包含公共字段"""

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    create_time = Column(BigInteger, nullable=False, comment="创建时间")
    update_time = Column(BigInteger, nullable=False, comment="更新时间")
    create_user = Column(BigInteger, nullable=True, comment="创建人")
    update_user = Column(BigInteger, nullable=True, comment="更新人")


class TbUser(BaseModel):
    """用户表"""

    __tablename__ = "tb_user"

    guid = Column(String(255), unique=True, nullable=False, comment="唯一编码")
    name = Column(String(255), nullable=False, comment="名字")
    account = Column(String(255), unique=True, nullable=False, comment="账号")
    passwd = Column(String(255), nullable=False, comment="密码")
    email = Column(String(255), nullable=True, comment="邮箱")
    phone = Column(String(255), nullable=True, comment="手机")


class TbWorkSpace(BaseModel):
    """工作空间表"""

    __tablename__ = "tb_work_space"

    code = Column(String(255), unique=True, nullable=False, comment="唯一编码")
    name = Column(String(255), nullable=False, comment="空间名称")
    description = Column(Text, nullable=True, comment="空间说明")
    extend = Column(Text, nullable=True, comment="扩展信息")


class TbDataSource(BaseModel):
    """数据源表"""

    __tablename__ = "tb_data_source"

    code = Column(String(255), unique=True, nullable=False, comment="唯一编码")
    name = Column(String(255), nullable=False, comment="数据源名称")
    platform = Column(String(255), nullable=False, comment="数据库类型")
    setting = Column(Text, nullable=False, comment="数据库配置信息")
    semantic = Column(Text, nullable=True, comment="数据源语义说明")
    description = Column(Text, nullable=True, comment="数据源说明")
    extend = Column(Text, nullable=True, comment="扩展信息")


class TbDataModel(BaseModel):
    """数据模型表"""

    __tablename__ = "tb_data_model"

    code = Column(String(255), unique=True, nullable=False, comment="唯一编码")
    name = Column(String(255), nullable=False, comment="模型名称")
    platform = Column(String(255), nullable=False, comment="数据库类型")
    type = Column(String(255), nullable=True, comment="模型类型:table,view")
    ds_id = Column(Integer, nullable=True, comment="所属数据源ID")
    semantic = Column(Text, nullable=True, comment="语义说明")
    summary = Column(Text, nullable=True, comment="摘要说明")
    knowledge = Column(Text, nullable=True, comment="外部知识")
    description = Column(Text, nullable=True, comment="描述信息")
    extend = Column(Text, nullable=True, comment="扩展信息")


class TbWorkSpaceRelation(BaseModel):
    """工作空间关系表"""

    __tablename__ = "tb_work_space_relation"

    ws_id = Column(Integer, nullable=False, comment="工作空间ID")
    resource_type = Column(String(255), nullable=False, comment="资源类型:data_source,data_model等")
    resource_id = Column(Integer, nullable=False, comment="资源ID")


class TbLlm(BaseModel):
    """大模型配置表"""

    __tablename__ = "tb_llm"

    provider = Column(String(255), nullable=False, comment="模型提供商")
    api_key = Column(String(255), nullable=True, comment="API密钥")
    base_url = Column(String(255), nullable=True, comment="API基础URL")
    model = Column(String(255), nullable=False, comment="模型名称")
    setting = Column(Text, nullable=True, comment="其他配置信息")
    description = Column(Text, nullable=True, comment="描述信息")
    extend = Column(Text, nullable=True, comment="扩展信息")


class TbAgent(BaseModel):
    """智能体主表"""

    __tablename__ = "tb_agent"

    name = Column(String(255), nullable=False, comment="智能体名称")
    description = Column(Text, nullable=True, comment="智能体描述")
    config = Column(Text, nullable=True, comment="智能体配置信息（JSON格式）")
    status = Column(String(255), nullable=False, default="active", comment="状态:active,inactive")
    extend = Column(Text, nullable=True, comment="扩展信息")


class TbAgentNode(BaseModel):
    """智能体节点配置表"""

    __tablename__ = "tb_agent_node"

    agent_id = Column(Integer, nullable=False, comment="智能体ID")
    name = Column(String(255), nullable=True, comment="节点名称")
    node_type = Column(
        String(255), nullable=False, comment="节点类型:start,end,llm,tool,python,subgraph"
    )
    config = Column(Text, nullable=True, comment="节点配置信息")
    description = Column(Text, nullable=True, comment="节点描述")
    extend = Column(Text, nullable=True, comment="扩展信息")


class TbAgentEdge(BaseModel):
    """智能体边配置表"""

    __tablename__ = "tb_agent_edge"

    agent_id = Column(Integer, nullable=False, comment="智能体ID")
    from_node_id = Column(Integer, nullable=False, comment="源节点ID")
    from_node_slot = Column(Integer, nullable=False, comment="源节点slot")
    to_node_id = Column(Integer, nullable=False, comment="目标节点ID")
    to_node_slot = Column(Integer, nullable=False, comment="目标节点slot")


class TbTool(BaseModel):
    """工具表"""

    __tablename__ = "tb_tool"

    tool = Column(String(255), nullable=False, comment="工具函数名")
    description = Column(Text, nullable=True, comment="工具描述")
    parameters = Column(Text, nullable=True, comment="工具参数定义")
    content = Column(Text, nullable=True, comment="工具代码内容")
    extend = Column(Text, nullable=True, comment="扩展信息")


class TbJob(BaseModel):
    """作业表"""

    __tablename__ = "tb_job"

    type = Column(String(255), nullable=False, comment="作业类型: agent 等")
    status = Column(
        String(255),
        nullable=False,
        default="waiting",
        comment="状态: waiting,running,stopped,success,failed",
    )
    setting = Column(Text, nullable=True, comment="配置(JSON)")
    description = Column(Text, nullable=True, comment="作业描述")
    extend = Column(Text, nullable=True, comment="扩展信息")
    begin_time = Column(BigInteger, nullable=True, comment="开始时间")
    end_time = Column(BigInteger, nullable=True, comment="结束时间")


class TbJobLog(BaseModel):
    """作业日志表"""

    __tablename__ = "tb_job_log"

    job_id = Column(Integer, nullable=False, comment="作业ID")
    content = Column(Text, nullable=False, comment="日志内容")
