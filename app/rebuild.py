from app.index_manager import build_and_save_chunk_index

# 直接执行一次建库
build_and_save_chunk_index()

print("建库完成，chunk_index.json，chunk_index.faiss")