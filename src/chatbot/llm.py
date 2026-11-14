import langchain
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
# from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
import os


load_dotenv()

os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')

llm = ChatOllama(model='qwen2.5:3b', temperature=0.7)
model = create_agent(llm)


def chatResponse(user_input: str) -> str:

    response = model.invoke({"messages" : [HumanMessage(user_input)]})
    return response['messages'][-1].content