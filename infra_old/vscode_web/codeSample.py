from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str="<%= connectionString %>")

agent = project_client.agents.get_agent("<%= agentId %>")

thread = project_client.agents.threads.create()
print(f"Created thread, ID: {thread.id}")

message = project_client.agents.messages.create(
    thread_id=thread.id,
    role="user",
    content="<%= userMessage %>"
)

run = project_client.agents.runs.create_and_process(
    thread_id=thread.id,
    agent_id=agent.id)

if run.status == "failed":
    print(f"Run failed: {run.last_error}")
else:
    messages = project_client.agents.messages.list(
        thread_id=thread.id, order=ListSortOrder.ASCENDING)

    for message in messages:
        if message.text_messages:
            print(f"{message.role}: {message.text_messages[-1].text.value}")
