import os

from dotenv import load_dotenv

from src.connectors.blob_storage_source import list_blob_documents
from src.connectors.sharepoint_graph_source import list_sharepoint_documents


load_dotenv()


def print_documents(label: str, documents) -> None:
    print(f"\n--- {label} ---")
    print(f"Documentos encontrados: {len(documents)}")

    for document in documents:
        print(f"\nSource ID: {document.source_id}")
        print(f"Título: {document.title}")
        print(f"Dominio: {document.domain}")
        print(f"Path: {document.path}")
        print(f"Texto: {document.text[:180]}...")


def main() -> None:
    blob_docs = list_blob_documents()
    print_documents("Azure Blob Storage", blob_docs)

    if os.getenv("SHAREPOINT_SITE_ID") and os.getenv("SHAREPOINT_DRIVE_ID"):
        sp_docs = list_sharepoint_documents()
        print_documents("SharePoint", sp_docs)
    else:
        print("\nSharePoint no configurado. Se omite prueba de Graph.")


if __name__ == "__main__":
    main()