import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient
from pypdf import PdfReader


DB_NAME = "GreenTech_DB"
COLLECTION_NAME = "manuals_vectors"
INDEX_NAME = "vector_index"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


def extract_pdf_text(pdf_path: Path) -> list[Document]:
    reader = PdfReader(str(pdf_path))
    documents = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        clean_text = " ".join(text.split())

        if not clean_text:
            continue

        for chunk_number, chunk in enumerate(split_text(clean_text), start=1):
            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "source": pdf_path.name,
                        "page": page_number,
                        "chunk": chunk_number,
                    },
                )
            )

    return documents


def split_text(text: str) -> list[str]:
    chunks = []
    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start = end - CHUNK_OVERLAP

    return chunks


def load_documents(pdf_paths: list[Path]) -> list[Document]:
    documents = []

    for pdf_path in pdf_paths:
        print(f"Leyendo {pdf_path.name}...")
        documents.extend(extract_pdf_text(pdf_path))

    return documents


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga PDFs locales en MongoDB Atlas Vector Search.")
    parser.add_argument("--reset", action="store_true", help="Elimina los vectores existentes antes de cargar.")
    args = parser.parse_args()

    load_dotenv()
    mongodb_uri = os.getenv("MONGODB_ATLAS_URI")

    if not mongodb_uri:
        raise RuntimeError("Falta MONGODB_ATLAS_URI en el archivo .env")

    pdf_paths = sorted(Path(".").glob("*.pdf"))
    if not pdf_paths:
        raise RuntimeError("No se encontraron archivos PDF en la raiz del proyecto.")

    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    collection = client[DB_NAME][COLLECTION_NAME]

    if args.reset:
        deleted = collection.delete_many({}).deleted_count
        print(f"Documentos eliminados antes de recargar: {deleted}")

    documents = load_documents(pdf_paths)
    if not documents:
        raise RuntimeError("No se pudo extraer texto util desde los PDF.")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vector_store = MongoDBAtlasVectorSearch(
        collection=collection,
        embedding=embeddings,
        index_name=INDEX_NAME,
    )

    inserted_ids = vector_store.add_documents(documents)
    print(f"Chunks cargados en MongoDB Atlas: {len(inserted_ids)}")
    print(f"Coleccion total actual: {collection.count_documents({})}")


if __name__ == "__main__":
    main()
