import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# DeepSeek API Key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# DeepSeek 接口地址
DEEPSEEK_BASE_URL = "https://api.deepseek.com/chat/completions"

# 模型名称
MODEL_NAME = "deepseek-chat"



# 本地知识文件路径
KNOWLEDGE_FILE = "data/knowledge.txt"
# KNOWLEDGE_FILE = "data/raw_docs/employee_handbook_sample.pdf"
# 企业资料目录
# 后续 txt / pdf / excel 都可以放到这个目录里
KNOWLEDGE_DIR = "data/raw_docs"



# OpenAI embedding 模型
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# 百炼 API Key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

# 百炼 OpenAI 兼容接口地址（北京地域）
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 你当前使用的 embedding 模型
EMBEDDING_MODEL = "text-embedding-v4"

# 向量维度
EMBEDDING_DIMENSIONS = 1024

#存储embedding的文件位置
CHUNK_INDEX_FILE = "data/chunk_index.json"

# 切割资料采用的方式
# 可选：
# 1. "blank_line_split"：按空行切分，适合排版规整的制度 / FAQ 文本
# 2. "fixed_size_overlap"：按固定长度切分，并保留重叠内容，适合长文本或排版不稳定文本
#3."paragraph_then_overlap"：先按段落 / 空行切，再对超长段落做 overlap 二次切分
# CHUNK_METHOD = "blank_line_split"
# CHUNK_METHOD = "fixed_size_overlap"
CHUNK_METHOD = "paragraph_then_overlap"

# fixed_size_overlap 模式下，每个 chunk 的最大字符数
CHUNK_SIZE = 300

# fixed_size_overlap 模式下，相邻 chunk 之间重叠的字符数
CHUNK_OVERLAP = 50

# 最终检索返回的参考资料数量
TOP_K = 2

# 索引检索返回的参考资料数量
HYBRID_RECALL_K = 10

# =========================
# Reranker 配置
# =========================

# 是否启用 reranker
USE_RERANKER = True

# reranker 提供方：
# - "llm"：使用 DeepSeek Chat 模拟 reranker
# - "dashscope"：使用阿里云百炼 qwen3-rerank
RERANKER_PROVIDER = "dashscope"

# 百炼 rerank 模型
DASHSCOPE_RERANK_MODEL = "qwen3-rerank"

# 百炼 rerank OpenAI 兼容接口地址
DASHSCOPE_RERANK_BASE_URL = "https://dashscope.aliyuncs.com/compatible-api/v1"

# reranker 前先保留多少条候选 chunk
# 注意：这里要大于 TOP_K，否则 reranker 没有选择空间
RERANK_CANDIDATE_K = 6

# reranker 分数阈值
# 当前统一使用 0-100 分制：
# - LLM reranker 本来就是 0-100
# - DashScope relevance_score 是 0-1，代码里会乘以 100
# reranker 主资料最低分数
# 最高分 chunk 只要达到这个分数，就可以作为主要参考资料保留
RERANK_PRIMARY_MIN_SCORE = 60

# reranker 补充资料最低分数
# 第 2 条及之后的 chunk 必须达到这个分数，才允许作为补充资料
RERANK_EXTRA_MIN_SCORE = 75

# reranker 补充资料最大分差
# 第 2 条及之后的 chunk，除了达到最低分，还不能和第一名差距过大
# 作用：过滤“同主题但明显不是当前问题答案”的资料
RERANK_EXTRA_MAX_GAP = 20

# 保留旧变量名，兼容旧函数或旧代码
RERANK_MIN_SCORE = RERANK_PRIMARY_MIN_SCORE

#faiss索引的权重
FAISS_WEIGHT = 0.5

#bm25索引的权重
BM25_WEIGHT = 0.5

#算法的平滑程度
RRF_K = 60

# 额外参考块的最低分数
# 作用：第 1 条之外的 chunk，分数低于这个值就不再传给大模型
# MIN_EXTRA_CHUNK_SCORE = 0.52

#是否返回调试参数
RETURN_DEBUG_INFO = True

#是否只返回用户说的话 不返回模型的回答
USE_ASSISTANT_HISTORY = False

#用户历史记录参考条数
MAX_HISTORY_TURNS = 5

# config.py
# FAISS 向量索引文件路径 (根据你的目录结构，放在 data 目录下)
FAISS_INDEX_FILE = "data/chunk_index.faiss"

# =========================
# Router 参数
# =========================

# 最低相似度阈值：
# 如果两个意图的分数都很低，说明 router 其实没那么确定。
ROUTER_MIN_SCORE = 0.45

# 分差阈值：
# rag_score 和 chat_score 至少拉开这么多，才认为是“明显胜出”。
ROUTER_MARGIN = 0.03

# 计算最终意图分时：
# 不能只看最像的 1 条样本，否则容易被单个样本误导。
BEST_SCORE_WEIGHT = 0.7
AVG_TOP_SCORE_WEIGHT = 0.3

# =========================
# LLM Router Fallback 配置
# =========================

# 是否在 Semantic Router 不确定时调用大模型兜底判断
USE_LLM_ROUTER_FALLBACK = True

# 是否保留关键词兜底
# 当前建议关闭：关键词只作为 debug 信号，不直接决定 intent
USE_KEYWORD_ROUTER_FALLBACK = False

# LLM Router 调用失败时的默认 intent
LLM_ROUTER_FAILED_DEFAULT_INTENT = "chat"

# =========================
# Index 自动重建配置
# =========================

# 启动时如果发现索引缺失 / 失效 / FAISS 文件损坏，是否自动重建索引
# 开发和面试演示阶段建议 True
# 生产环境建议谨慎开启，避免意外产生大量 embedding API 调用
AUTO_REBUILD_INDEX_ON_STARTUP = True

# =========================
# LLM Provider 配置
# =========================

# 控制最终回答模型使用哪个提供方
# 默认 deepseek，保证原项目稳定
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek").lower()

# DeepSeek 最终回答模型温度
DEEPSEEK_TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2"))

# Ollama 本地服务地址
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Ollama 本地模型名，要和 ollama list 里一致
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3-4b-instruct-local")

# Ollama 本地模型推理参数
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.8"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))
OLLAMA_REPEAT_PENALTY = float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.15"))


# 文档入库处理流程版本
# 当 document_loader / document_processor / document_chunker 的逻辑变化时，手动加 1
DOCUMENT_PIPELINE_VERSION = "v6"

# metadata 结构版本
# 当 metadata 字段设计变化时，手动加 1
METADATA_SCHEMA_VERSION = "v1"