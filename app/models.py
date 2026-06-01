# 定义参数格式
from pydantic import BaseModel

class AskRequest(BaseModel):
    
    question:str
    # 【新增】session_id 用来区分不同的对话窗口，默认为 "default"
    session_id: str = "default_user"


class AgentDemoRequest(BaseModel):
    """最小版 controlled tool calling agent demo 的请求参数。"""

    question: str
    session_id: str | None = None
    # request-level 授权上下文，危险工具不能由模型自己授权。
    allow_rebuild_index: bool = False
