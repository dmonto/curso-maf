from src.rag.local_retriever import search_knowledge


def main() -> None:
    queries = [
        "No puedo acceder a la VPN desde Windows 11",
        "Cómo decidir prioridad de un ticket de VPN",
        "El ERP devuelve error 500",
    ]

    for query in queries:
        print(f"\n--- QUERY: {query} ---")
        results = search_knowledge(query=query, top_k=3)

        for result in results:
            print(f"\nFuente: {result['source_id']}")
            print(f"Título: {result['title']}")
            print(f"Score: {result['score']}")
            print(f"Texto: {result['text'][:250]}...")


if __name__ == "__main__":
    main()