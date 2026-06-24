import os

from dotenv import load_dotenv

from src.connectors.blob_storage_source import list_blob_documents
from src.connectors.sharepoint_graph_source import list_sharepoint_documents
from src.indexing.corporate_sync import sync_documents_to_raw_folder
from src.indexing.incremental_updater import run_incremental_update


load_dotenv()


def main() -> None:
    documents = []

    print("\n--- Leyendo documentos desde Azure Blob Storage ---")
    blob_docs = list_blob_documents()
    print(f"Documentos Blob: {len(blob_docs)}")
    documents.extend(blob_docs)

    if os.getenv("SHAREPOINT_SITE_ID") and os.getenv("SHAREPOINT_DRIVE_ID"):
        print("\n--- Leyendo documentos desde SharePoint ---")
        sp_docs = list_sharepoint_documents()
        print(f"Documentos SharePoint: {len(sp_docs)}")
        documents.extend(sp_docs)
    else:
        print("\nSharePoint no configurado. Se omite.")

    print("\n--- Exportando documentos normalizados a raw/corporate ---")
    written_paths = sync_documents_to_raw_folder(documents)

    for path in written_paths:
        print(f"Escrito: {path}")

    print("\n--- Ejecutando actualización incremental del índice ---")
    result = run_incremental_update()

    print("\nResultado:")
    print(f"Documentos en índice local: {result['local_index']['documents_count']}")
    print(f"Chunks en índice local: {result['local_index']['chunks_count']}")

    for item in result["results"]:
        print(
            f"{item['source_id']} | {item['status']} | "
            f"{item['action']} | uploaded={item['uploaded']} | deleted={item['deleted']}"
        )


if __name__ == "__main__":
    main()