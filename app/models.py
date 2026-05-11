# 定义参数格式
from pydantic import BaseModel

class AskRequest(BaseModel):
    
    question:str
    # 【新增】session_id 用来区分不同的对话窗口，默认为 "default"
    session_id: str = "default_user"