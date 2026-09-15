import os
import sys

from langchain.messages import HumanMessage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llmpick import pick_llm
from utils.database import DatabaseUtil
from models.schema import AgentSchema
from langchain_core.messages import HumanMessage

#........................AI Agent Code.......................................#

def curate_ques(state: AgentSchema) -> AgentSchema:

    user_question = state.user_question #why are we using . here?? because it is a pydantic model object

    llm = pick_llm("low")  # Pick the LLM based on the desired level

    response = llm.invoke(f"Curate the following question: {user_question}")

    state.curated_ques = response  # Update the state with the curated question
    state.messages = state.messages + [HumanMessage(content=f"Curated Question: {response}")]  # Append the curated question to the messages list

    return state #when i return state, it will return the updated state object with the curated question.
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

    state.prompt_query_context = prompt  # Update the state with the prompt query context

    llm = pick_llm("medium")  # Pick the LLM based on the desired level
    generated_sql_query = llm.invoke(prompt)  # Generate the SQL query using the LLM
    state.generated_sql_query = generated_sql_query  # Update the state with the generated SQL query


    return state


# llm_obj = pick_llm("low")
# print(llm_obj.invoke("What is the capital of France?"))