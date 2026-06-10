from foundry_local_sdk import Configuration, FoundryLocalManager

config = Configuration(app_name="curso_foundry_local")
FoundryLocalManager.initialize(config)

manager = FoundryLocalManager.instance

models = manager.catalog.list_models()

for m in models:
    print("alias:", getattr(m, "alias", None))
    print("id:   ", getattr(m, "model_id", None))
    print("---")

# Descarga y registra proveedores de ejecución: CPU, GPU, NPU si aplica
manager.download_and_register_eps()

# Selecciona un modelo del catálogo local
model = manager.catalog.get_model("phi-3-mini-4k")

# Descarga el modelo la primera vez
model.download()

# Carga el modelo en memoria
model.load()

client = model.get_chat_client()

messages = [
    {"role": "user", "content": "Explica qué es Foundry Local en dos frases."}
]

for chunk in client.complete_streaming_chat(messages):
    content = chunk.choices[0].delta.content if len(chunk.choices) else ''
    if content:
        print(content, end="", flush=True)

model.unload()