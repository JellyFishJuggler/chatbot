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
from src.chatbot.llm.tools import search_career_documents, log_job_application, get_job_application, generate_interview_questions, analyze_jd_match

load_dotenv()

os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')

tools = [search_career_documents, log_job_application, get_job_application, generate_interview_questions, analyze_jd_match]

llm = ChatOllama(model="qwen2.5:3b", temperature=0.2)
# llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash')
llm = llm.bind_tools(tools)
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
    SYSTEM = """You are a career and interview preparation assistant.

Rules:
- Use your tools whenever the user asks about their resume, skills, projects, JD match, interview practice, or tracking/listing job applications.
- Never claim you saved, updated, or retrieved an application or resume detail without calling the appropriate tool first.
- Rely ONLY on facts returned by your tools or stated in the conversation. Do not guess or fabricate details.
- For casual greetings (like "hi", "hello"), respond naturally without calling tools."""

    result = llm.invoke([SystemMessage(content=SYSTEM)] + state["messages"])
    return {"messages": [result]}   

graph_builder = StateGraph(State)
graph_builder.add_node("llmchatbot", chatResponse)
tools_node = ToolNode(tools=tools)
graph_builder.add_node("tools",tools_node)
graph_builder.add_conditional_edges("llmchatbot", tools_condition)
graph_builder.add_edge("tools","llmchatbot")
graph_builder.add_edge(START, "llmchatbot")
# graph_builder.add_edge("llmchatbot", END)

graph = graph_builder.compile(checkpointer=memory)

def _responseChatBot(_humanMessage: str, chatGraph: StateGraph = graph, thread_id:str = 'default_user'):

    config = {"configurable":{"thread_id":thread_id}}

    response = graph.invoke({"messages":[HumanMessage(_humanMessage)]}, config=config)
    return response["messages"][-1].content