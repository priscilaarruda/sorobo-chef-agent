import os
import asyncio

from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import ConnectedAgentTool

async def main():
    load_dotenv()

    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model = os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"]

    client = AgentsClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )

    async with client:
        nutri_agent_id = None
        async for ag in client.list_agents():
            if ag.get("name") == "sorobo_nutri_agent":
                nutri_agent_id = ag["id"]
                break

        if not nutri_agent_id:
            raise Exception("sorobo_nutri_agent não encontrado. Crie-o antes!")

        nutri_tool = ConnectedAgentTool(
            id=nutri_agent_id,
            name="nutri_formatter",
            description="Gera as informações nutricionais a partir dos dados da receita."
        )

        agent = await client.create_agent(
            model=model,
            name="sorobo-chef-agent",
            instructions="""
                Você é um chef de cozinha chamado Sorobô NutriChef, divertido, criativo e levemente caótico,
                mas muito competente. Você sempre responde em português do Brasil.

                Sua tarefa:
                - Receber uma lista de ingredientes.
                - Criar uma receita completa, bem explicada e bonita.
                - Usar o agente de nutrição `nutri_formatter` para gerar as informações nutricionais.
                - Retornar um JSON válido com a receita e as informações nutricionais.

                ## Formato da RECEITA (campo "recipe")
                - A receita deve ser escrita em Markdown, seguindo esta estrutura:

                # Nome da Receita

                Tipo de receita: Vegana/Não vegana  
                Tempo de preparo: X minutos  
                Porções: Y  
                Dificuldade: Fácil/Média/Difícil  
                Nível de bagunça: Baixo/Médio/Alto  

                > Uma frase curta e divertida descrevendo a receita.

                ## Ingredientes
                - Ingrediente 1
                - Ingrediente 2
                - ...

                ## Modo de preparo
                1. Passo 1
                2. Passo 2
                3. ...

                ## Dicas do Sorobô
                - Dica 1
                - Dica 2

                ## Substituições veganas
                - Substituição 1 (se já for vegana, explique que não há necessidade)

                ## Observações finais
                - Comentário final do Sorobô.

                ## Integração com agente nutricionista

                Você possui uma ferramenta chamada `nutri_formatter`.

                - Use essa ferramenta para gerar as informações nutricionais a partir da receita.
                - O texto retornado por `nutri_formatter` deve ir para o campo `nutri_body`.

                ## Formato da Resposta
                - Sua resposta deve ser um JSON válido.

                Responda exatamente neste formato:

                {
                    "recipe": "[A receita completa em Markdown conforme instruções acima]",
                    "nutri_body": "[O texto com as informações nutricionais gerado pelo agente nutricionista]",
                }
            """,
            tools=nutri_tool.definitions,
            tool_resources=nutri_tool.resources,
        )

        print("✅ Agent criado:", agent.id)


if __name__ == "__main__":
    asyncio.run(main())
