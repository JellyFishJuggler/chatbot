import langchain
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
# from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
# from pydantic import BaseModel
from typing_extensions import TypedDict, Annotated
import os

from src.chatbot.llm.rag import retrieve_context

load_dotenv()

os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')

# llm = ChatOllama(model='qwen2.5:3b', temperature=0.7)
llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash')
model = create_agent(llm)


class State(TypedDict):
    """Messages have the type of list. The add_messages function in the annotation defines how this state should be updated. (in our case it appends messages to the list rather than overwriting them)"""
    messages: Annotated[list, add_messages]


def chatResponse(state: State) -> dict:

    result = model.invoke({"messages": state["messages"]})
    return {"messages":[result['messages'][-1]]}

graph_builder = StateGraph(State)
graph_builder.add_node("llmchatbot", chatResponse)
graph_builder.add_edge(START, "llmchatbot")
graph_builder.add_edge("llmchatbot", END)

graph = graph_builder.compile()

def _responseChatBot(_humanMessage: str, chatGraph: StateGraph = graph):

    context = retrieve_context(_humanMessage)

    SYSTEM = f"""You are a helpful, direct assistant. Answer the user's question strictly using the provided context below.

        Rules:
        - Rely ONLY on the facts inside <context>. Do not guess or assume anything outside it.
        - If the context says "No context available" or does not contain the answer, clearly say you don't have enough information to answer that.
        - Keep your response concise and clear.

        <context>
        {context}
        </context>"""

    response = graph.invoke({"messages":[SystemMessage(content=SYSTEM), HumanMessage(_humanMessage)]})
    return response["messages"][-1].content