"""
LangChain version of answer generation tool.
Demonstrates LangChain's integration with OpenAI for answer generation.
"""

from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import json
import os


@tool  
def generate_answer(question: str, sources: str) -> str:
    """
    Generate a comprehensive tax answer based on sources.
    
    Args:
        question: The user's tax question
        sources: JSON string containing legislation and case law sources
        
    Returns:
        JSON string with generated answer
    """
    try:
        # Parse sources
        sources_data = json.loads(sources) if isinstance(sources, str) else sources
        
        # Use LangChain's ChatOpenAI for answer generation
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Format sources for prompt
        formatted_sources = ""
        for source in sources_data.get('legislation', []):
            formatted_sources += f"WETGEVING: {source['source']}: {source['content']}\n\n"
        for source in sources_data.get('case_law', []):
            formatted_sources += f"JURISPRUDENTIE: {source['source']}: {source['content']}\n\n"
        
        # Generate answer using LangChain
        messages = [
            SystemMessage(content="""Je bent een Nederlandse belastingexpert. Geef een uitgebreid, accuraat antwoord op belastingvragen op basis van de gegeven bronnen. 
            
Gebruik alleen de informatie uit de bronnen. Vermeld altijd de specifieke bronnen in je antwoord."""),
            HumanMessage(content=f"""Vraag: {question}

Beschikbare bronnen:
{formatted_sources}

Geef een uitgebreid antwoord met bronvermeldingen.""")
        ]
        
        response = llm(messages)
        
        return json.dumps({
            "success": True,
            "data": response.content,
            "metadata": {"question": question, "sources_used": len(sources_data.get('legislation', [])) + len(sources_data.get('case_law', []))}
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "data": None
        }, ensure_ascii=False)