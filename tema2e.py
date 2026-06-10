import openai
from foundry_local_sdk import Configuration, FoundryLocalManager

config = Configuration(app_name="curso_foundry_local")
FoundryLocalManager.initialize(config)

manager = FoundryLocalManager.instance
manager.download_and_register_eps()

model = manager.catalog.get_model("phi-3-mini-4k")
model.download()
model.load()

# Arranca un endpoint REST local compatible con OpenAI
manager.start_web_service()
base_url = f"{manager.urls[0]}/v1"

client = openai.OpenAI(
    base_url=base_url,
    api_key="none"
)

response = client.chat.completions.create(
    model=model.id,
    messages=[
        {"role": "system", "content": "Eres un asistente técnico."},
        {"role": "user", "content": "Resume las ventajas de ejecutar modelos locales."}
    ],
    stream=True
)

for chunk in response:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)

model.unload()
manager.stop_web_service()