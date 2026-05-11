import math
from app.embedding_api import get_embedding
from app.config import (
    ROUTER_MIN_SCORE,
    ROUTER_MARGIN,
    BEST_SCORE_WEIGHT,
    AVG_TOP_SCORE_WEIGHT,
    USE_LLM_ROUTER_FALLBACK,
    USE_KEYWORD_ROUTER_FALLBACK,
)

from app.llm_router import llm_route_fallback



# =========================
# Chat 意图样本
# =========================
CHAT_EXAMPLES = [
    # 问候 / 礼貌
    "你好",
    "谢谢",
    "好的我知道了",
    "明白了",
    "嗯嗯",
    "再见",

    # 普通闲聊
    "你能陪我聊聊吗",
    "讲个笑话",
    "你是谁",
    "你叫什么名字",
    "我叫什么名字",

    # 学习 / 情绪 / 建议类
    "我现在该先学什么",
    "我今天状态不好怎么调整",
    "你觉得我下一步该做什么",
    "我有点焦虑怎么办",
    "帮我解释一下这个概念",
    "我该怎么找工作",
    "学习RAG项目的流程应该怎么安排",
    "RAG项目下一步怎么学",
    "我该怎么准备AI应用开发岗位面试",
    "我该怎么推进当前AI项目",
    "这个项目后续怎么优化",
]

# =========================
# RAG 意图样本
# =========================
RAG_EXAMPLES = [
    # 报销制度
    "报销500元以下谁审批",
    "报销500到2000元怎么审批",
    "报销金额超过2000元怎么审批",
    "差旅报销流程是什么",
    "发票提交有什么要求",

    # 请假制度
    "事假怎么请",
    "病假超过1天需要什么",
    "年假怎么申请",
    "调休是怎么规定的",
    "怎么请假",
    "请假需要谁审批",
    "公司职位调整怎么申请",
    "公司岗位变更流程是什么",
    "员工晋升流程是什么",
    "内部调岗怎么申请",
    "提岗需要什么流程",
    "公司内部职位变更有什么规定",

    # 审批 / 流程 / 员工手册
    "员工手册里关于请假的规定是什么",
    "审批流程是什么",
    "这个需要审批吗",
    "这个要提交什么材料",
    "公司制度是怎么规定的",

    # 多轮追问常见表达
    "那再高一点呢",
    "那病假呢",
    "那事假呢",
    "请假流程怎么走",
    "报销流程怎么走",
    "审批流程怎么走",
    "员工手册里的审批流程是什么",
    "公司制度里的申请流程是什么",
    # 医药文档 / 药品说明书 / SOP
    "青禾感冒颗粒适用于什么症状",
    "青禾感冒颗粒的不良反应有哪些",
    "青禾感冒颗粒怎么服用",
    "洛宁舒敏片的不良反应有哪些",
    "洛宁舒敏片可以治疗哮喘急性发作吗",
    "胃舒安胶囊适用于什么情况",
    "胃舒安胶囊怎么服用",
    "药品入库需要核对哪些信息",
    "冷链药品到货后怎么处理",
    "库房温湿度怎么记录",
    "近效期药品怎么管理",
    "过期药品怎么处理",
    "疑似药品不良反应怎么登记",
    "两个药品能不能一起使用资料里有没有说明",
]

# =========================
# 领域关键词兜底
# =========================
RAG_DOMAIN_KEYWORDS = [
    "员工手册",
    "公司制度",
    "制度",
    "规定",
    "审批流程",
    "报销流程",
    "请假流程",
    "入职流程",
    "离职流程",
    "转正流程",
    "审批",
    "申请",
    "报销",
    "差旅",
    "发票",
    "请假",
    "年假",
    "病假",
    "事假",
    "调休",
    "加班",
    "考勤",
    "旷工",
    "入职",
    "离职",
    "转正",
    "绩效",
    "薪资",
    "合同",
    "药品说明书",
    "适应症",
    "用法用量",
    "不良反应",
    "禁忌",
    "注意事项",
    "药品",
    "批号",
    "有效期",
    "批准文号",
    "入库",
    "冷链",
    "温湿度",
    "近效期",
    "过期药品",
    "SOP",
    "质量负责人",
    "联合用药",
    "医生",
    "药师",
]


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    计算两个向量的余弦相似度
    """
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def contains_domain_keyword(text: str) -> bool:
    """
    判断文本中是否包含明显的知识库领域关键词

    作用：
    - 当语义分数不够确定时，作为 rag 兜底依据
    - 尤其适合多轮追问，例如：
      上一轮：报销500到2000元怎么审批？
      当前轮：那再高一点呢？
    """
    clean_text = text.strip()

    if not clean_text:
        return False

    return any(keyword in clean_text for keyword in RAG_DOMAIN_KEYWORDS)


def build_intent_router() -> dict:
    """
    启动时预计算意图样本向量

    注意：
    - 这些 embedding 会在 FastAPI 启动时构建一次
    - 不应该每次请求都重新构建
    """
    print("🧭 正在构建增强版 Semantic Router 意图原型...")

    chat_vectors = []
    for text in CHAT_EXAMPLES:
        chat_vectors.append({
            "text": text,
            "embedding": get_embedding(text)
        })

    rag_vectors = []
    for text in RAG_EXAMPLES:
        rag_vectors.append({
            "text": text,
            "embedding": get_embedding(text)
        })

    print("✅ 增强版 Semantic Router 构建完成！")

    return {
        "chat_examples": chat_vectors,
        "rag_examples": rag_vectors
    }


def get_top_matches(
    query_embedding: list[float],
    examples: list[dict],
    top_n: int = 3
) -> list[dict]:
    """
    找出 query_embedding 和某一类样本中最接近的 top_n 条

    返回示例：
    [
        {"text": "事假怎么请", "score": 0.82},
        {"text": "怎么请假", "score": 0.79}
    ]
    """
    matches = []

    for item in examples:
        score = cosine_similarity(query_embedding, item["embedding"])
        matches.append({
            "text": item["text"],
            "score": float(score),
        })

    matches.sort(key=lambda x: x["score"], reverse=True)

    return matches[:top_n]


def calculate_intent_score(top_matches: list[dict]) -> float:
    """
    计算某个意图类别的最终分数

    为什么不只看第一名？
    - 只看 best_score 容易被单个样本误导
    - 加入 top3 平均分后，能看出整体是否都接近这个意图
    """
    if not top_matches:
        return 0.0

    best_score = top_matches[0]["score"]
    avg_score = sum(item["score"] for item in top_matches) / len(top_matches)

    final_score = (
        best_score * BEST_SCORE_WEIGHT
        + avg_score * AVG_TOP_SCORE_WEIGHT
    )

    return float(final_score)


def semantic_route(route_context: str, intent_router: dict) -> tuple[str, dict]:
    """
    用 route_context 做语义路由

    返回：
    - intent: "chat" 或 "rag"
    - debug_info: 路由调试信息

    当前增强点：
    1. 不只比较单个最高相似度
    2. 增加 top3 平均分
    3. 增加分差判断
    4. 增加领域关键词兜底
    5. 返回更完整的 debug 信息
    """

    clean_context = route_context.strip()

    if not clean_context:
        return "chat", {
            "route_strategy": "empty_context_default_chat",
            "decision_reason": "route_context 为空，默认走 chat",
        }

    # 1. 当前问题 / 上下文转 embedding
    query_embedding = get_embedding(clean_context)

    # 2. 分别找出 chat / rag 最接近的 top3 样本
    top_chat_matches = get_top_matches(
        query_embedding=query_embedding,
        examples=intent_router["chat_examples"],
        top_n=3,
    )

    top_rag_matches = get_top_matches(
        query_embedding=query_embedding,
        examples=intent_router["rag_examples"],
        top_n=3,
    )

    # 3. 分别计算两个意图的最终分数
    chat_final_score = calculate_intent_score(top_chat_matches)
    rag_final_score = calculate_intent_score(top_rag_matches)

    score_gap = rag_final_score - chat_final_score
    domain_keyword_hit = contains_domain_keyword(clean_context)

    # 4. 决策逻辑
    if rag_final_score >= ROUTER_MIN_SCORE and score_gap >= ROUTER_MARGIN:
        intent = "rag"
        route_strategy = "semantic_clear_rag"
        decision_reason = "rag 语义分数明显高于 chat"

    elif chat_final_score >= ROUTER_MIN_SCORE and score_gap <= -ROUTER_MARGIN:
        intent = "chat"
        route_strategy = "semantic_clear_chat"
        decision_reason = "chat 语义分数明显高于 rag"

    else:
        # 5. 语义分数不够明确时，优先使用 LLM Router 兜底
        if USE_LLM_ROUTER_FALLBACK:
            intent, llm_router_debug = llm_route_fallback(clean_context)
            route_strategy = f"llm_fallback_{intent}"
            decision_reason = "语义分数不够明确，调用 LLM Router 进行兜底判断"

        # 6. 如果关闭 LLM Router，才考虑关键词兜底
        elif USE_KEYWORD_ROUTER_FALLBACK and domain_keyword_hit:
            intent = "rag"
            route_strategy = "domain_keyword_fallback_rag"
            decision_reason = "语义分数不够明确，但 route_context 包含知识库领域关键词，使用关键词兜底"
            llm_router_debug = None

        else:
            intent = "chat"
            route_strategy = "uncertain_default_chat"
            decision_reason = "语义分数不够明确，默认走 chat"
            llm_router_debug = None
        # 判断最终决策来源，方便 debug 展示
    if route_strategy in ["semantic_clear_rag", "semantic_clear_chat"]:
        route_decision_source = "semantic"
    elif route_strategy.startswith("llm_fallback"):
        route_decision_source = "llm_fallback"
    elif route_strategy == "domain_keyword_fallback_rag":
        route_decision_source = "keyword_fallback"
    else:
        route_decision_source = "default"

    fallback_used = route_decision_source in ["llm_fallback", "keyword_fallback"]

    # 如果前面没有进入 LLM fallback 分支，补一个默认值
    if "llm_router_debug" not in locals():
        llm_router_debug = None

    # 6. 调试信息
    debug_info = {
        "intent": intent,
        "route_strategy": route_strategy,
        "decision_reason": decision_reason,

        "chat_final_score": chat_final_score,
        "rag_final_score": rag_final_score,
        "score_gap_rag_minus_chat": score_gap,

        "best_chat_score": top_chat_matches[0]["score"] if top_chat_matches else None,
        "best_chat_example": top_chat_matches[0]["text"] if top_chat_matches else None,
        "best_rag_score": top_rag_matches[0]["score"] if top_rag_matches else None,
        "best_rag_example": top_rag_matches[0]["text"] if top_rag_matches else None,

        "top_chat_matches": top_chat_matches,
        "top_rag_matches": top_rag_matches,

        "domain_keyword_hit": domain_keyword_hit,
        "domain_keyword_detected": domain_keyword_hit,
        "fallback_used": fallback_used,
        "route_decision_source": route_decision_source,
        "llm_router_debug": llm_router_debug,

        "router_min_score": ROUTER_MIN_SCORE,
        "router_margin": ROUTER_MARGIN,
    }

    return intent, debug_info