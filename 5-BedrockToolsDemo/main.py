import boto3
import streamlit as st
from datetime import datetime
from duckduckgo_search import DDGS

client = boto3.client("bedrock-runtime", region_name="us-west-2")
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"


def get_today_date_tool():
    st.write("### Using the tool `get_today_date`")
    res = {"today": datetime.today().strftime("%Y-%m-%d")}
    st.markdown("Tool Result")
    st.markdown(res)
    st.markdown("---")
    return res


def search_tool(inputs):
    st.write("### Using the tool `search_tool`")
    query = inputs.get("query", "")
    if not query:
        return {"results": []}

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, region="us-en", safesearch="Moderate", max_results=3):
            results.append(r)

    res = {"results": results}
    st.markdown("Duck Duck Go Search Results")
    st.code(res)
    st.markdown("---")
    return res


# Tool config
datetime_tool_spec = {
    "name": "get_today_date",
    "description": "Returns today's date in YYYY-MM-DD format. Always use this to understand time. Use it before searching any current events.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

search_tool_spec = {
    "name": "search_tool",
    "description": "Searches the web to get the most current information. Returns 3 relevant links",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    }
}


tool_config = {
    "tools": [{"toolSpec": datetime_tool_spec}, {"toolSpec": search_tool_spec}],
    "toolChoice": {"auto": {}}
}

# Tool routing function
def run_tool(name, inputs):
    if name == "get_today_date":
        return get_today_date_tool()
    elif name == "search_tool":
        return search_tool(inputs)
    raise ValueError(f"Unknown tool: {name}")


def ask_bedrock(prompt):
    messages = [
        {
            "role": "user",
            "content": [{"text": prompt}]
        }
    ]

    while True:
        res = client.converse(
            modelId=model_id,
            messages=messages,
            toolConfig=tool_config
        )

        output_msg = res["output"]["message"]
        messages.append(output_msg)

        # Check if the model wants to use a tool
        tool_use = next((b["toolUse"] for b in output_msg["content"] if "toolUse" in b), None)

        # Handle each toolUse one by one
        if tool_use:
            result_data = run_tool(tool_use["name"], tool_use["input"])

            tool_result_msg = {
                "role": "user",
                "content": [{
                    "toolResult": {
                        "toolUseId": tool_use["toolUseId"],
                        "content": [{"json": result_data}],
                        "status": "success"
                    }
                }]
            }
            messages.append(tool_result_msg)
            continue

        return messages


# Streamlit UI
st.title("🛠️ Bedrock Tool Use Demo")

user_input = st.text_area("Ask the model")
if st.button("Ask"):
    with st.spinner("Thinking..."):
        result = ask_bedrock(user_input)
        st.json(result)
