import os
import time
import json

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from dotenv import load_dotenv

from utils.recipe_pdf import save_recipe_pdf

def get_agent_id(client: AgentsClient, name: str) -> str:
    for ag in client.list_agents():
        if ag.get("name") == name:
            return ag["id"]
    raise RuntimeError(f"Agent '{name}' não encontrado.")

def main():
    load_dotenv()

    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]

    client = AgentsClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )

    sorobo_id = get_agent_id(client, "sorobo-chef-agent")

    print("=== Bem-vindo ao Sorobô NutriChef ===\n")

    ingredientes = input("Informe os ingredientes disponíveis:\n> ").strip()

    print("\nGerando receita personalizada...\n")

    thread = client.threads.create()

    client.messages.create(
        thread_id=thread.id,
        role="user",
        content=(
            f"Usuário informou estes ingredientes: {ingredientes}.\n"
        ),
    )

    run = client.runs.create(
        thread_id=thread.id,
        agent_id=sorobo_id,
    )

    while run.status in ("queued", "in_progress", "requires_action"):
        time.sleep(1)
        run = client.runs.get(thread_id=thread.id, run_id=run.id)

    if run.status != "completed":
        print(f"Erro: run terminou com status {run.status}")
        return
    
    messages = client.messages.list(thread_id=thread.id, order="desc")

    assistant_message = next(
        (m for m in messages if m.role == "assistant"),
        None,
    )

    if assistant_message is None:
        print("Nenhuma mensagem do assistant encontrada.")
        return

    assistant_text_parts = []
    for block in assistant_message.content:
        text_obj = getattr(block, "text", None)
        if text_obj is not None:
            assistant_text_parts.append(text_obj.value)

    assistant_text = "".join(assistant_text_parts)

    try:
        start = assistant_text.find("{")
        end = assistant_text.rfind("}")

        if start != -1 and end != -1:
            json_str = assistant_text[start : end + 1]
        else:
            json_str = assistant_text

        data = json.loads(json_str)
        recipe_text = data.get("recipe", "")
        nutr_body = data.get("nutri_body", "")
    except json.JSONDecodeError:
        print("\nA resposta não veio em JSON válido.\n")
        recipe_text = assistant_text
        nutr_body = assistant_text

    if not recipe_text:
        print("Erro: não foi possível extrair a receita da resposta do agente.")
        return
    
    print("Gerando PDF da receita...\n")
    pdf_path = save_recipe_pdf(recipe_text, output_dir="recipes", filename_hint="sorobo_recipe")
    print(f"PDF criado em: {pdf_path}\n")

    if not nutr_body:
        print("Erro: não foi possível extrair as informações nutricionais da resposta do agente.")
        return

    print("Gerando PDF das informações nutricionais...\n")
    pdf_path = save_recipe_pdf(nutr_body, output_dir="recipes", filename_hint="sorobo_nutritional_info")
    print(f"PDF criado em: {pdf_path}\n")

if __name__ == "__main__":
    main()
