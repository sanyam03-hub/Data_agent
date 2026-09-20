import os
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llmpick import pick_llm
from utils.etl_tools import ETLTools
from models.schema import ETLAgentSchema
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langchain.tools import tool


#------------------------------------ AGENT TOOLS ------------------------------------#


@tool
def extract_load_tool(url:str, output_folder:str, format:str) -> str:
    """Extract data from `url` and save into `output_folder` in given `format`."""
    etl_tools = ETLTools()
    return etl_tools.extract_load(url, output_folder, format)


@tool
def transform_load_tool(input_file_path:str,output_folder:str,output_format:str, user_question:str) -> str:
    """Generate and execute a pandas transformation on `input_file_path` and save results to `output_folder`."""
    etl_tools = ETLTools()

    # Resolve project root and normalize input/output paths so they map to this workspace
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # Try direct path first; if missing, search under project data folders for the basename
    abs_input = input_file_path
    if not os.path.exists(abs_input):
        basename = os.path.basename(input_file_path)
        found = None
        for root, dirs, files in os.walk(os.path.join(project_root, 'data')):
            if basename in files:
                found = os.path.join(root, basename)
                break
        if found:
            abs_input = found

    # Normalize output folder to be inside project
    if os.path.isabs(output_folder):
        parts = output_folder.replace('\\', '/').split('/')
        if 'data' in parts:
            data_index = parts.index('data')
            rel = os.path.join(*parts[data_index:])
            abs_output = os.path.join(project_root, rel)
        else:
            abs_output = os.path.join(project_root, os.path.basename(output_folder))
    else:
        abs_output = os.path.join(project_root, output_folder)

    os.makedirs(abs_output, exist_ok=True)

    top_3_rows = etl_tools.transform_load_context(abs_input)

    llm = pick_llm("claude")

    prompt = f"""
            You are a Python Data Analyst who uses Pandas to analyze data. 
            You need to provide only the Pandas Code that will help to perform the right ETL operations on the data stored in the file : {abs_input}
            as per the user's question. Do not provide any explanation or comments, only
            the code should be provided. The code should be in a format that can be executed 
            in a Python environment with Pandas installed. 
            Don't write anything else than Pandas Code. \n
            Create the Pandas Dataframe from the data stored in the file : {abs_input} and then 
            write the code to transform and save the data at {abs_output}.
            Here's the user's question: {user_question}\n
            Here's the context of the data you will be analyzing: {top_3_rows}\n
        """

    response = llm.invoke(prompt).content 

    # Optional Cleaning
    pandas_code = response.strip().strip('```').strip().lstrip('python').strip()

    # Execute the Pandas code and detect created files in output folder
    before = set(os.listdir(abs_output))
    results = etl_tools.execute_code(pandas_code, output_folder=abs_output)
    after = set(os.listdir(abs_output))
    created = list(after - before)

    created_msg = f"Created files: {created}" if created else "No new files detected in output folder."

    return f"The data is transformed and saved at {abs_output} in {output_format} format. \n\n Pandas Code Executed: \n {pandas_code} \n\n Execution Result: \n {results}\n\n{created_msg}"


# Toolkit 
tools = [extract_load_tool, transform_load_tool]

llm = pick_llm("claude")
llm_bind = llm.bind_tools(tools)


# ---------------------------------------- AGENT GRAPH ---------------------------------------- #

def llm_node(state:ETLAgentSchema):

    messages = state.messages

    prompt = f"""
            You are a Python Data Analyst who has access to tools that can extract and load, 
            transform and load data. You will be provided with a user's question 
            and you would need to perform the right ETL operations as per the user's question. 
            If the operation is performed then inform the user and end the coversation.
            Here's the chat history: {messages}\n
    """

    final_answer = llm_bind.invoke(prompt)

    state.messages = messages + [final_answer]

    return state


def tool_node(state:ETLAgentSchema):
    """
    This node is responsible for invoking the appropriate tool based on the user's question and the context provided by the LLM.
    """

    tools_results = []

    tools_by_name = {tool.name: tool for tool in tools}

    tool_calls = state.messages[-1].tool_calls

    for tool_call in tool_calls:

        tool = tools_by_name[tool_call['name']]
        observation = tool.invoke(tool_call['args'])

        # If transform tool failed due to missing file, try to auto-extract from a detected URL
        if tool_call['name'] == 'transform_load_tool' and isinstance(observation, str) and observation.startswith('File not found'):
            # search prior human messages for a URL
            found_url = None
            for m in state.messages:
                try:
                    text = m.content
                except Exception:
                    continue
                urls = re.findall(r"https?://[\w\-._~:/?#\[\]@!$&'()*+,;=%]+", text)
                if urls:
                    found_url = urls[0]
                    break

            if found_url:
                # attempt extraction to the default folder mentioned in the prompt
                extract_output = extract_load_tool(found_url, 'data/extract', 'csv')
                tools_results.append(ToolMessage(content=extract_output, tool_call_id=tool_call['id']))

                # retry the transform after extraction
                observation = tool.invoke(tool_call['args'])

        tools_results.append(ToolMessage(content=observation, tool_call_id = tool_call['id']))

    state.messages = state.messages + tools_results

    return state   


# Nodes & Edges
etl_analyst_graph = StateGraph(ETLAgentSchema)
etl_analyst_graph.add_node("llm_node", llm_node)
etl_analyst_graph.add_node("tool_node", tool_node)

etl_analyst_graph.add_edge(START, "llm_node")

def is_tool_call(state:ETLAgentSchema):
    tool_calls = state.messages[-1].tool_calls

    if tool_calls:
        return "tool_node"
    else:
        return "end"

etl_analyst_graph.add_conditional_edges(
    "llm_node", is_tool_call,
    {
        "tool_node": "tool_node",
        "end": END
    }
)

etl_analyst_graph.add_edge("tool_node", "llm_node")


if __name__ == "__main__":
    # Compile the Graph
    etl_analyst = etl_analyst_graph.compile()
    # Optional
    from IPython.display import display, Image
    img = Image(etl_analyst.get_graph().draw_mermaid_png())
    with open("etl_analyst_graph.png", "wb") as f:
        f.write(img.data)

    response = etl_analyst.invoke(
        {"messages":[HumanMessage(content="I want to extract the data from the API endpoint 'https://pokeapi.co/api/v2/pokemon' and save it to data/extract folder in the csv folder")]}
    )

    response = etl_analyst.invoke(
         {"messages":[HumanMessage(content=f"""
            I want to transform the data stored in the 'c:\\Data_Agent\\data\\extract\\extracted_data.csv' file 
            and save the transformed data in the 'c:\\Data_Agent\\data\\transform' folder in the csv format.
            The transformation should filter the data to show bulbasaur pokemon only.
""")]}
    )    

    print(response)
