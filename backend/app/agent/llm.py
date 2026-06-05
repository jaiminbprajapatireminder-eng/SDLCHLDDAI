import os

from langchain_core.tools import BaseTool

# Try Groq first, fall back to Gemini
# Use llama-3.1-8b-instant by default for higher rate limits (6000 TPM / 30000 TPD vs 1000 TPD on 70b).
# Override with GROQ_MODEL env var to use a larger model if you have a paid Groq tier.
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


def build_agent_llm(tools: list[BaseTool]):
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        from langchain_groq import ChatGroq

        llm = ChatGroq(
            model=GROQ_MODEL,
            temperature=0.2,
            api_key=groq_key,
        )
        return llm.bind_tools(tools)

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.2,
            api_key=gemini_key,
        )
        return llm.bind_tools(tools)

    raise ValueError(
        "No API key found. Set GROQ_API_KEY or GEMINI_API_KEY."
    )
