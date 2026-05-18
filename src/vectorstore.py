from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient


DB_NAME = "GreenTech_DB"
COLLECTION_NAME = "manuals_vectors"
INDEX_NAME = "vector_index"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def get_vector_search(mongodb_uri: str) -> MongoDBAtlasVectorSearch:
    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    collection = client[DB_NAME][COLLECTION_NAME]

    return MongoDBAtlasVectorSearch(
        collection=collection,
        embedding=get_embeddings(),
        index_name=INDEX_NAME,
    )
