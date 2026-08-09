import os

import chromadb


store_path = os.environ["CG1_PROBE_STORE"]
log_path = os.environ["FSYNCWATCH_LOG"]
client = chromadb.PersistentClient(path=store_path)
collection = client.get_or_create_collection(
    "probe_units", metadata={"hnsw:space": "cosine"}
)
with open(log_path, "a", encoding="utf-8") as handle:
    handle.write("=== MARK before upsert ===\n")
collection.upsert(
    ids=["u1"],
    embeddings=[[0.1, 0.2, 0.3]],
    documents=["hello"],
    metadatas=[{"k": "v"}],
)
with open(log_path, "a", encoding="utf-8") as handle:
    handle.write("=== MARK after upsert ===\n")
print("count:", collection.count())
