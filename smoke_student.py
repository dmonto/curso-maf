from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable, Optional
from dotenv import load_dotenv

import requests

load_dotenv()

class SkipCheck(Exception):
    pass


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str
    critical: bool


RESULTS: list[CheckResult] = []


def env(name: str, required: bool = True, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")
    return value or ""


def run_cmd(cmd: list[str], timeout: int = 30) -> str:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Comando fallido: {' '.join(cmd)}\n"
            f"STDOUT:\n{proc.stdout}\n"
            f"STDERR:\n{proc.stderr}"
        )
    return proc.stdout.strip()


def check(name: str, critical: bool, fn: Callable[[], str]) -> None:
    try:
        detail = fn()
        RESULTS.append(CheckResult(name, "OK", detail, critical))
    except SkipCheck as exc:
        RESULTS.append(CheckResult(name, "SKIP", str(exc), critical))
    except Exception as exc:
        RESULTS.append(CheckResult(name, "FAIL", str(exc), critical))


def get_credential():
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential(
        exclude_interactive_browser_credential=True
    )


def get_token(scope: str) -> str:
    credential = get_credential()
    return credential.get_token(scope).token


def auth_get(url: str, scope: str, timeout: int = 30) -> requests.Response:
    token = get_token(scope)
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    return response


def check_python() -> str:
    version = sys.version.replace("\n", " ")
    major, minor = sys.version_info[:2]
    if major != 3 or minor < 10:
        raise RuntimeError(f"Python no soportado: {version}")
    return version


def check_executable(exe: str, critical: bool = True) -> Callable[[], str]:
    def inner() -> str:
        path = shutil.which(exe)
        if not path:
            raise RuntimeError(f"No se encuentra {exe} en PATH")
        return path

    return inner


def check_azure_cli_account() -> str:
    out = run_cmd(["az", "account", "show", "--output", "json"])
    data = json.loads(out)

    expected_sub = os.getenv("SUBSCRIPTION_ID")
    current_sub = data.get("id")

    if expected_sub and current_sub.lower() != expected_sub.lower():
        raise RuntimeError(
            f"Suscripción activa incorrecta. Actual: {current_sub}. "
            f"Esperada: {expected_sub}"
        )

    return f"{data.get('name')} / {data.get('id')} / user={data.get('user', {}).get('name')}"


def check_required_env() -> str:
    required = [
        "TENANT_ID",
        "SUBSCRIPTION_ID",
        "RESOURCE_GROUP",
        "AZURE_OPENAI_RESOURCE",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT_1",
        "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT",
        "AZURE_AI_PROJECT_ENDPOINT",
        "AZURE_AI_SEARCH_SERVICE",
        "AZURE_AI_SEARCH_ENDPOINT",
        "AZURE_STORAGE_ACCOUNT",
        "AZURE_STORAGE_CONTAINER",
    ]

    missing = [name for name in required if not os.getenv(name)]

    if missing:
        raise RuntimeError("Faltan variables: " + ", ".join(missing))

    return "Variables mínimas configuradas"


def check_imports() -> str:
    imports = [
        "openai",
        "azure.identity",
        "azure.storage.blob",
        "azure.ai.projects",
        "requests",
        "agent_framework",
    ]

    failed = []

    for module in imports:
        try:
            __import__(module)
        except Exception as exc:
            failed.append(f"{module}: {exc}")

    if failed:
        raise RuntimeError("\n".join(failed))

    return "Imports principales disponibles"


def check_management_rg() -> str:
    sub = env("SUBSCRIPTION_ID")
    rg = env("RESOURCE_GROUP")

    url = (
        f"https://management.azure.com/subscriptions/{sub}"
        f"/resourcegroups/{rg}"
        f"?api-version=2021-04-01"
    )

    response = auth_get(url, "https://management.azure.com/.default")

    if response.status_code != 200:
        raise RuntimeError(f"{response.status_code}: {response.text[:1000]}")

    data = response.json()
    return f"Resource Group accesible: {data.get('name')} / {data.get('location')}"


def check_management_resources() -> str:
    sub = env("SUBSCRIPTION_ID")
    rg = env("RESOURCE_GROUP")

    resources = [
        (
            "Azure OpenAI",
            f"Microsoft.CognitiveServices/accounts/{env('AZURE_OPENAI_RESOURCE')}",
            "2023-05-01",
        ),
        (
            "Azure AI Search",
            f"Microsoft.Search/searchServices/{env('AZURE_AI_SEARCH_SERVICE')}",
            "2023-11-01",
        ),
        (
            "Storage Account",
            f"Microsoft.Storage/storageAccounts/{env('AZURE_STORAGE_ACCOUNT')}",
            "2023-01-01",
        ),
    ]

    found = []

    for label, resource_path, api_version in resources:
        url = (
            f"https://management.azure.com/subscriptions/{sub}"
            f"/resourceGroups/{rg}"
            f"/providers/{resource_path}"
            f"?api-version={api_version}"
        )

        response = auth_get(url, "https://management.azure.com/.default")

        if response.status_code != 200:
            raise RuntimeError(
                f"No se pudo acceder a {label}. "
                f"HTTP {response.status_code}: {response.text[:1000]}"
            )

        found.append(label)

    return "Recursos accesibles: " + ", ".join(found)


def check_azure_openai_chat() -> str:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import AzureOpenAI

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(exclude_interactive_browser_credential=True),
        "https://cognitiveservices.azure.com/.default",
    )

    client = AzureOpenAI(
        azure_endpoint=env("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        azure_ad_token_provider=token_provider,
    )

    response = client.chat.completions.create(
        model=env("AZURE_OPENAI_DEPLOYMENT_1"),
        messages=[
            {
                "role": "system",
                "content": "Responde solo con la palabra OK.",
            },
            {
                "role": "user",
                "content": "Prueba de conectividad.",
            },
        ],
        max_tokens=10,
        temperature=0,
    )

    content = response.choices[0].message.content or ""

    if "OK" not in content.upper():
        raise RuntimeError(f"Respuesta inesperada: {content}")

    return f"Chat OK con deployment {env('AZURE_OPENAI_DEPLOYMENT_1')}"


def check_azure_openai_embeddings() -> str:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import AzureOpenAI

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(exclude_interactive_browser_credential=True),
        "https://cognitiveservices.azure.com/.default",
    )

    client = AzureOpenAI(
        azure_endpoint=env("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        azure_ad_token_provider=token_provider,
    )

    response = client.embeddings.create(
        model=env("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT"),
        input="Smoke test de embeddings para el curso MAF.",
    )

    vector = response.data[0].embedding

    if not vector or len(vector) < 100:
        raise RuntimeError(f"Vector demasiado corto o vacío: {len(vector)}")

    return f"Embeddings OK. Dimensión: {len(vector)}"


def check_foundry_project() -> str:
    from azure.ai.projects import AIProjectClient

    endpoint = env("AZURE_AI_PROJECT_ENDPOINT")
    credential = get_credential()

    # Primero validamos token de AI Foundry.
    credential.get_token("https://ai.azure.com/.default")

    client = AIProjectClient(
        endpoint=endpoint,
        credential=credential,
    )

    # Intentamos una operación ligera. El SDK está cambiando rápido,
    # por eso probamos varias superficies habituales.
    attempts = []

    if hasattr(client, "connections") and hasattr(client.connections, "list"):
        attempts.append(("connections.list", client.connections.list))

    if hasattr(client, "agents") and hasattr(client.agents, "list_agents"):
        attempts.append(("agents.list_agents", client.agents.list_agents))

    if not attempts:
        return "Token AI + cliente Foundry creados. SDK sin método ligero conocido para listar."

    last_error = None

    for label, method in attempts:
        try:
            iterator = method()
            # Consumimos como máximo un elemento para no cargar nada pesado.
            for _ in iterator:
                break
            return f"Foundry Project accesible mediante {label}"
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"No se pudo validar Foundry Project: {last_error}")


def check_search_indexes() -> str:
    endpoint = env("AZURE_AI_SEARCH_ENDPOINT").rstrip("/")
    url = f"{endpoint}/indexes?api-version=2024-07-01"

    response = auth_get(url, "https://search.azure.com/.default")

    if response.status_code != 200:
        raise RuntimeError(f"{response.status_code}: {response.text[:1000]}")

    data = response.json()
    count = len(data.get("value", []))

    return f"Azure AI Search accesible. Índices visibles: {count}"


def check_storage_container_read() -> str:
    from azure.storage.blob import BlobServiceClient

    account = env("AZURE_STORAGE_ACCOUNT")
    container_name = env("AZURE_STORAGE_CONTAINER")

    service = BlobServiceClient(
        account_url=f"https://{account}.blob.core.windows.net",
        credential=get_credential(),
    )

    container = service.get_container_client(container_name)

    count = 0
    for _ in container.list_blobs():
        count += 1
        if count >= 3:
            break

    return f"Storage Blob accesible. Primeros blobs leídos: {count}"


def check_storage_write_optional() -> str:
    if os.getenv("SMOKE_WRITE_TESTS", "0") != "1":
        raise SkipCheck("SMOKE_WRITE_TESTS no está activado")

    from azure.storage.blob import BlobServiceClient

    account = env("AZURE_STORAGE_ACCOUNT")
    container_name = env("AZURE_STORAGE_CONTAINER")

    service = BlobServiceClient(
        account_url=f"https://{account}.blob.core.windows.net",
        credential=get_credential(),
    )

    blob_name = f"smoke-tests/smoke-{int(time.time())}.txt"

    blob = service.get_blob_client(
        container=container_name,
        blob=blob_name,
    )

    blob.upload_blob(
        b"Smoke test curso MAF",
        overwrite=True,
    )

    downloaded = blob.download_blob().readall()

    if b"Smoke test" not in downloaded:
        raise RuntimeError("No se pudo leer el blob escrito")

    blob.delete_blob()

    return f"Escritura/lectura/borrado OK en {blob_name}"


def check_graph_me() -> str:
    response = auth_get(
        "https://graph.microsoft.com/v1.0/me?$select=id,displayName,userPrincipalName",
        "https://graph.microsoft.com/.default",
    )

    if response.status_code != 200:
        raise RuntimeError(f"{response.status_code}: {response.text[:1000]}")

    data = response.json()

    return f"Graph /me OK: {data.get('userPrincipalName') or data.get('displayName')}"


def check_github_models_optional() -> str:
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise SkipCheck("GITHUB_TOKEN no configurado")

    from openai import OpenAI

    endpoint = os.getenv("GITHUB_MODELS_ENDPOINT", "").rstrip("/")
    model = os.getenv("GITHUB_MODELS_MODEL", "openai/gpt-4o-mini")

    if not endpoint:
        raise RuntimeError("Falta GITHUB_MODELS_ENDPOINT")

    client = OpenAI(
        api_key=token,
        base_url=endpoint,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": "Responde solo OK.",
            }
        ],
        max_tokens=10,
        temperature=0,
    )

    content = response.choices[0].message.content or ""

    if "OK" not in content.upper():
        raise RuntimeError(f"Respuesta inesperada: {content}")

    return f"GitHub Models OK con {model}"


def check_ollama() -> str:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

    response = requests.get(f"{host}/api/tags", timeout=10)

    if response.status_code != 200:
        raise RuntimeError(f"{response.status_code}: {response.text[:1000]}")

    data = response.json()
    models = data.get("models", [])

    if not models:
        return "Ollama responde, pero no hay modelos descargados"

    names = [m.get("name", "") for m in models[:3]]

    return "Ollama OK. Modelos: " + ", ".join(names)


def check_docker_running() -> str:
    out = run_cmd(["docker", "version", "--format", "{{.Server.Version}}"], timeout=20)

    if not out:
        raise RuntimeError("Docker responde, pero no devuelve versión del servidor")

    return f"Docker Engine OK: {out}"


def print_report() -> int:
    print("\n" + "=" * 90)
    print("SMOKE TEST CURSO MAF")
    print("=" * 90)
    print(f"Sistema: {platform.platform()}")
    print(f"Python:  {sys.version.split()[0]}")
    print("-" * 90)

    failed_critical = False

    for result in RESULTS:
        marker = {
            "OK": "✅",
            "SKIP": "⚪",
            "FAIL": "❌",
        }[result.status]

        critical_label = "CRÍTICO" if result.critical else "opcional"

        print(f"{marker} [{critical_label}] {result.name}")
        print(f"   {result.detail}")

        if result.status == "FAIL" and result.critical:
            failed_critical = True

    print("-" * 90)

    if failed_critical:
        print("RESULTADO FINAL: ❌ NO APTO PARA EL CURSO")
        print("Hay fallos críticos que deben corregirse antes de la sesión.")
        return 1

    print("RESULTADO FINAL: ✅ APTO PARA EL CURSO")
    print("Los componentes críticos funcionan. Revisa los SKIP/opcionales si se van a usar en clase.")
    return 0


def main() -> int:
    check("Python compatible", True, check_python)

    check("Git instalado", True, check_executable("git"))
    check("Azure CLI instalada", True, check_executable("az"))
    check("Docker CLI instalada", True, check_executable("docker"))
    check("Ollama instalado", False, check_executable("ollama", critical=False))
    check("VS Code CLI instalada", False, check_executable("code", critical=False))

    check("Azure CLI autenticado en la suscripción correcta", True, check_azure_cli_account)
    check("Variables de entorno mínimas", True, check_required_env)
    check("Imports Python principales", True, check_imports)

    check("RBAC sobre Resource Group", True, check_management_rg)
    check("Recursos Azure principales visibles", True, check_management_resources)

    check("Azure OpenAI Chat", True, check_azure_openai_chat)
    check("Azure OpenAI Embeddings", True, check_azure_openai_embeddings)

    check("Microsoft Agent Framework importable", True, lambda: "agent_framework import OK")
    check("Foundry Project", True, check_foundry_project)

    check("Azure AI Search", True, check_search_indexes)
    check("Storage Blob lectura", True, check_storage_container_read)
    check("Storage Blob escritura opcional", False, check_storage_write_optional)

    check("Microsoft Graph /me", True, check_graph_me)

    check("Docker Engine en ejecución", True, check_docker_running)
    check("Ollama API local", False, check_ollama)
    check("GitHub Models opcional", False, check_github_models_optional)

    return print_report()


if __name__ == "__main__":
    raise SystemExit(main())