import sqlite3
import langchain
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
# from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.runnables import RunnableConfig
# from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
# from pydantic import BaseModel
from typing_extensions import TypedDict, Annotated
import os

from src.chatbot.llm.rag import retrieve_context

load_dotenv()

os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')

llm = ChatOllama(model='dolphin-phi:2.7b', temperature=0.7)
# llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash')
connection = sqlite3.connect('/tmp/chat_memory.db', check_same_thread=False)
model = create_agent(llm)
memory = SqliteSaver(connection)

class State(TypedDict):
    """Messages have the type of list. The add_messages function in the annotation defines how this state should be updated. (in our case it appends messages to the list rather than overwriting them)"""
    messages: Annotated[list, add_messages]


def getHistory(thread_id:str) -> list[str]:
    
    config = {"configurable":{"thread_id":thread_id}}
    getGraphState = graph.get_state(config)

    mesg = getGraphState.values.get("messages",[])
    chatHistory = list()

    for m in mesg:
        if isinstance(m, HumanMessage):
            chatHistory.append({"role":"user", "content":m.content})
        elif isinstance(m, AIMessage):
            chatHistory.append({"role":"ai", "content":m.content})

    return chatHistory

def chatResponse(state: State, config: RunnableConfig) -> dict:

    user_id = config['configurable']['thread_id']
    latest_query = state['messages'][-1].content
    context = retrieve_context(latest_query, user_id=user_id)
    SYSTEM = f"""You are a helpful, direct assistant. Answer the user's questions using the provided context below.

        Rules:
        - Rely ONLY on the facts inside <context>. Do not guess, assume, or introduce outside information.
        - If the context says "No context available" or does not contain the answer, clearly say you don't have enough information to answer.
        - Keep your responses concise, clear, and conversational.
        - If the user sends a casual greeting (like "hi", "hello", "wassup), respond naturally and ask how you can help with the documents.
        - Do not force document-related responses when the user is simply engaging in casual conversation.
        
        <context>
        {context}
        </context>"""
    result = model.invoke({"messages":[SystemMessage(content=SYSTEM)] + state['messages']})
    return {"messages":[result['messages'][-1]]}

graph_builder = StateGraph(State)
graph_builder.add_node("llmchatbot", chatResponse)
graph_builder.add_edge(START, "llmchatbot")
graph_builder.add_edge("llmchatbot", END)

graph = graph_builder.compile(checkpointer=memory)

def _responseChatBot(_humanMessage: str, chatGraph: StateGraph = graph, thread_id:str = 'default_user'):

    config = {"configurable":{"thread_id":thread_id}}

    response = graph.invoke({"messages":[HumanMessage(_humanMessage)]}, config=config)
    return response["messages"][-1].content