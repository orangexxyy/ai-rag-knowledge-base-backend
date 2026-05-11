# 统一定义返回数据结构
def success_response(message="操作成功",data=None):
    return{
        "success":True,
        "message":message,
        "data":data,
        "error":None
    }
def error_response(message: str, error: str, data=None):
    return {
        "success": False,
        "message": message,
        "data": data,
        "error": error
    }
    
import re


def is_obvious_chat_message(message: str) -> bool:
    """
    判断是否是明显普通聊天 / 礼貌收尾。

    作用：
    - 这类输入不需要进入 Semantic Router
    - 更不应该被历史 RAG 上下文带偏
    """

    if not message or not message.strip():
        return True

    # 统一清洗：去掉空格、标点，转小写
    text = message.strip().lower()
    normalized = re.sub(r"[\s，。！？、,.!?~～]+", "", text)

    obvious_chat_messages = {
        "你好",
        "您好",
        "嗨",
        "hello",
        "hi",

        "谢谢",
        "谢谢你",
        "感谢",
        "感谢你",

        "好的",
        "好",
        "ok",
        "okay",
        "收到",
        "明白",
        "明白了",
        "知道了",
        "嗯",
        "嗯嗯",

        # 【重点】组合型礼貌收尾
        "好的谢谢",
        "好谢谢",
        "收到谢谢",
        "明白了谢谢",
        "知道了谢谢",

        "再见",
        "拜拜",
    }

    return normalized in obvious_chat_messages