from src.state import SupportSessionMemory
from src.storage import AzureTableSessionMemoryStore

store = AzureTableSessionMemoryStore.from_env()

memory = SupportSessionMemory()
memory.servicio = "vpn"
memory.ubicacion = "casa"
memory.usuarios_afectados = 1

store.save(
    user_id="diego-demo",
    session_id="smoke-test",
    memory=memory,
)

loaded = store.load(
    user_id="diego-demo",
    session_id="smoke-test",
)

print(loaded.to_json() if loaded else "No encontrada")