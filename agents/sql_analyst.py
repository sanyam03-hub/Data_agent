import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llmpick import pick_llm
from utils.database import DatabaseUtil
from models.schema import AgentSchema, JudgeSchema
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END

#........................AI Agent Code.......................................#

def curate_ques(state: AgentSchema) -> AgentSchema:

    user_question = state.user_question #why are we using . here?? because it is a pydantic model object

    llm = pick_llm("low")  # Pick the LLM based on the desired level

    response = llm.invoke(f"Curate the following question: {user_question}").content

    new_messages = state.messages + [HumanMessage(content=f"Curated Question: {response}")]
    return {"curated_ques": response, "messages": new_messages}
    #This allows the calling function to access the updated state and continue processing with the curated question.


def prompt_query_context(state: AgentSchema) -> AgentSchema:

    curated_question = state.curated_ques

    connection = {
        "host": os.getenv("host"),
        "port": int(os.getenv("port", 5432)),
        "user": os.getenv("user"),
        "password": os.getenv("password"),
        "dbname": os.getenv("database")
    }

    obj = DatabaseUtil(connection)

    schema_info = obj.schema_details("public")  # Fetch the schema information from the database

    # Constructing the prompt query for the agent to generate the SQL query
    prompt = f"""
    You are an SQL analyst agent. Your task is to convert the user's natural language 
    query into Postgres SQL query that can be executed on the database. You are provided 
    with the user's original query and the schema details of the database, including
    table names, column names, data types, and sample data for each table so that 
    you can understand the structure of the database and generate an accurate SQL query.
    Unless user explicitly asks for specific number of rows, always limit the output to 10 rows.
    Note - Just generate the SQL query without any explanation or additional text because
    this query will be executed directly on the database. So, the output should be SQL
    ready to be executed without any modifications.

    User's Original Query: {curated_question}
    Database Schema Details: {schema_info}

    """

    return {"prompt_query_context": prompt}

# llm_obj = pick_llm("low")
# print(llm_obj.invoke("What is the capital of France?"))

#genrating SQL query Node
def generate_sql_query(state: AgentSchema) -> AgentSchema:

    prompt = state.prompt_query_context  # Retrieve the prompt query context from the state

    llm = pick_llm("medium")  # Pick the LLM based on the desired level

    generated_sql_query = llm.invoke(prompt).content  # Generate the SQL query using the LLM

    return {"generated_sql_query": generated_sql_query}



#is safe Node
def is_safe(state: AgentSchema) -> AgentSchema:
    sql_query = state.generated_sql_query

    llm = pick_llm("medium")  # Pick the LLM based on the desired level
    llm_judge = llm.with_structured_output(JudgeSchema)  # Create a structured output version of the LLM for judging

    prompt = f"""
    You are an SQL Judge for data security. Your task is to determine whether the SQL query is 
    safe or not. The SQL query should only be used for data retrieval and should not modify the 
    database in any way. Neither the SQL query nor the prompt should contain any SQL commands that can modify the
    database, such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or any other commands that can change
    the structure or content of the database. If the SQL query is safe, respond with 'Yes' otherwise respond with 
    'No'. Additionally, provide comments explaining your decision.
    Here's the SQL query to evaluate: {sql_query}"""

    response = llm_judge.invoke(prompt).model_dump()  # Invoke the structured output LLM with the prompt
    return {"is_safe_sql_response": response["answer"], "comments": response["comments"]}



#Canceled SQL Node
def canceled_sql(state: AgentSchema) -> AgentSchema:

    comments = state.comments  # Retrieve the comments from the state

    final = f"The SQL query was canceled due to safety concerns. Comments from the judge: {comments}"
    new_messages = state.messages + [AIMessage(content=f"{final}")]
    return {"final_answer": [final], "messages": new_messages}


#Excute SQL Node
def execute_sql(state: AgentSchema) -> AgentSchema:
    sql_query = state.generated_sql_query  # Retrieve the generated SQL query from the state

    connection = {
        "host": os.getenv("host"),
        "port": int(os.getenv("port", 5432)),
        "user": os.getenv("user"),
        "password": os.getenv("password"),
        "dbname": os.getenv("database")
    }

    obj = DatabaseUtil(connection)

    try:
        result = obj.execute_query(sql_query)  # Execute the SQL query using the database utility
        final = f"The SQL query executed successfully. Result: {result}"
        return {"sql_query_expected_result": str(result), "final_answer": [final]}
    except Exception as e:
        return {"final_answer": [f"Error executing SQL query: {str(e)}"]}


#Representing the final answer Node
def represent_final_answer(state: AgentSchema) -> AgentSchema:

    execution_result = state.sql_query_expected_result  # Retrieve the expected result of the SQL query from the state
    curated_question = state.curated_ques  # Retrieve the curated question from the state

    llm = pick_llm("low")  # Pick the LLM based on the desired level

    prompt = f"""
    You are an SQL analyst agent. Your task is to provide a final answer to the user based on the
    execution result of the SQL query and the user's original question. The final answer should be
    concise, clear, and directly address the user's query. Avoid including any SQL code or technical
    details in the final answer. The final answer should be in a user-friendly format that is easy to
    understand. If the execution result is empty or does not provide a clear answer to the user's question, explain this in the final answer. \n
    Here is the execution result: {execution_result} \n
    Here is the user's original question: {curated_question}
    """

    llm_response = llm.invoke(prompt).content  # Get the final answer from the LLM
    new_messages = state.messages + [AIMessage(content=f"{llm_response}")]
    return {"messages": new_messages}


#....................................Graph Building........................................#
sql_agent_graph = StateGraph(AgentSchema)  # Create a state graph for the SQL agent using the AgentSchema

#NOdes
sql_agent_graph.add_node(curate_ques,name="curate_ques")
sql_agent_graph.add_node(prompt_query_context,name="prompt_query_context")
sql_agent_graph.add_node(generate_sql_query,name="generate_sql_query")
sql_agent_graph.add_node(is_safe,name="is_safe")
sql_agent_graph.add_node(canceled_sql,name="canceled_sql")
sql_agent_graph.add_node(execute_sql,name="execute_sql")
sql_agent_graph.add_node(represent_final_answer,name="represent_final_answer")


#Edges
sql_agent_graph.add_edge(START, "curate_ques")
sql_agent_graph.add_edge("curate_ques", "prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql_query")
sql_agent_graph.add_edge("generate_sql_query", "is_safe")

#conditional edge function
def is_safe_sql_edge(state: AgentSchema) -> str:
    is_safe = state.is_safe_sql_response  # Retrieve the safety evaluation result from the state

    if is_safe.lower() == "yes":
        return "execute_sql"  # If the SQL query is safe, proceed to execute it
    else:
        return "canceled_sql"  # If the SQL query is not safe, cancel the execution

sql_agent_graph.add_conditional_edges("is_safe", is_safe_sql_edge,
                                      {
                                          "execute_sql": "execute_sql",
                                          "canceled_sql": "canceled_sql"
                                      })

# sql_agent_graph.add_edge("is_safe", "execute_sql")  # Add an edge from the safety evaluation node to the execute SQL node
# sql_agent_graph.add_edge("is_safe", "canceled_sql")  # Add an edge from the safety evaluation node to the canceled SQL node
sql_agent_graph.add_edge("canceled_sql", END)  # Add an edge from the canceled SQL node to the final answer representation node
sql_agent_graph.add_edge("execute_sql", "represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer", END)  # Add an edge from the final answer representation node to the END node

if __name__ == "__main__":
    # Compile the state graph into an executable agent
    sql_analyst = sql_agent_graph.compile()

    # Display the graph as a PNG image
    from IPython.display import display, Image
    img = Image(sql_analyst.get_graph().draw_mermaid_png())
    with open("sql_analyst_graph.png", "wb") as f:
        f.write(img.data)


    input_schema = {
        "messages": [],
        "user_question": "What are the different types of Payment Methods we have in our database?",
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe_sql_response": "No",
        "comments": "",
        "sql_query_expected_result": "",
        "final_answer": []
    }


    # Execute the agent with the input schema
    sql_analyst_response = sql_analyst.invoke(input_schema)

    print(sql_analyst_response)  # Print the final response from the SQL analyst agent