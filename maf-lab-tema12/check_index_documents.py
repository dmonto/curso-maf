from src.rag.document_indexer import build_document_index
from src.rag.indexed_search import search_indexed_documents


def main() -> None:
    print("\n--- CONSTRUYENDO ÍNDICE DOCUMENTAL ---")
    index_payload = build_document_index()

    print(f"Documentos indexados: {index_payload['documents_count']}")
    print(f"Chunks generados: {index_payload['chunks_count']}")
    print(f"Generado en: {index_payload['generated_at_utc']}")

    queries = [
        ("VPN Windows 11 no accede", None),
        ("ERP error 500 varios usuarios", None),
        ("prioridad ticket problema individual VPN", None),
        ("error 500", "erp"),
    ]

    for query, domain in queries:
        print(f"\n--- QUERY: {query} | DOMAIN: {domain or '-'} ---")
        results = search_indexed_documents(query=query, domain=domain, top_k=3)

        for result in results:
            print(f"\nFuente: {result['source_id']}")
            print(f"Título: {result['title']}")
            print(f"Dominio: {result['domain']}")
            print(f"Score: {result['score']}")
            print(f"Texto: {result['text'][:250]}...")


if __name__ == "__main__":
    main()