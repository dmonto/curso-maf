import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
)

response = client.chat.completions.create(
    model=os.environ["AZURE_OPENAI_DEPLOYMENT_CHAT"],
    messages=[
        {"role": "system", "content": "Eres un asistente técnico claro y preciso."},
        {"role": "user", "content": "Explica qué es Azure AI Foundry en dos frases."}
    ],
)

print(response.choices[0].message.content)