from src.rag.document_indexer import build_document_index
from src.vector.azure_ai_search_store import rebuild_vector_index, vector_search


def main() -> None:
    print("\n--- 1. Reconstruyendo índice documental local ---")
    build_document_index()

    print("\n--- 2. Creando índice vectorial en Azure AI Search ---")
    rebuild_vector_index()

    queries = [
        ("No puedo entrar a la red privada desde Windows 11", None),
        ("El sistema de gestión devuelve error del servidor a muchos usuarios", None),
        ("Cómo clasifico una incidencia individual de VPN", None),
        ("Error 500 en ERP", "erp"),
    ]

    print("\n--- 3. Probando búsquedas ---")

    for query, domain in queries:
        print(f"\nQUERY: {query}")
        print(f"DOMAIN: {domain or '-'}")

        results = vector_search(
            query=query,
            domain=domain,
            top_k=3,
            hybrid=True,
        )

        for result in results:
            print(f"\nFuente: {result['source_id']}")
            print(f"Título: {result['title']}")
            print(f"Dominio: {result['domain']}")
            print(f"Score: {result['score']}")
            print(f"Texto: {result['text'][:250]}...")


if __name__ == "__main__":
    main()