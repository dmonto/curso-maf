import os
import requests

endpoint = "https://models.github.ai/inference/chat/completions"
token = os.environ["GITHUB_TOKEN"]

payload = {
    "model": "openai/gpt-4.1",
    "messages": [
        {
            "role": "system",
            "content": "Eres un asistente técnico claro y preciso."
        },
        {
            "role": "user",
            "content": "Explica qué aporta GitHub Models al desarrollo de aplicaciones de IA."
        }
    ],
    "temperature": 0.3
}

headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {token}",
    "X-GitHub-Api-Version": "2022-11-28",
    "Content-Type": "application/json"
}

response = requests.post(endpoint, headers=headers, json=payload)
response.raise_for_status()

data = response.json()
print(data["choices"][0]["message"]["content"])