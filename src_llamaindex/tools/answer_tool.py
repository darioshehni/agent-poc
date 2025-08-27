"""
LlamaIndex version of answer generation tool.
Demonstrates LlamaIndex's approach to response synthesis.
"""

from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI
import json
import os


def generate_answer_impl(question: str, sources: str) -> str:
    """
    Generate comprehensive tax answer using LlamaIndex's response synthesis.
    
    Args:
        question: The user's tax question
        sources: JSON string containing legislation and case law sources
        
    Returns:
        JSON string with generated answer
    """
    try:
        # Parse sources
        sources_data = json.loads(sources) if isinstance(sources, str) else sources
        
        # Use LlamaIndex OpenAI LLM
        llm = OpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Format sources for LlamaIndex style processing
        formatted_sources = ""
        for source in sources_data.get('legislation', []):
            formatted_sources += f"WETGEVING: {source['source']}: {source['content']}\n\n"
        for source in sources_data.get('case_law', []):
            formatted_sources += f"JURISPRUDENTIE: {source['source']}: {source['content']}\n\n"
        
        # LlamaIndex style prompt for answer synthesis
        prompt = f"""Je bent een Nederlandse belastingexpert. Analyseer de volgende bronnen en beantwoord de gebruikersvraag uitgebreid en accuraat.

Vraag: {question}

Beschikbare bronnen:
{formatted_sources}

Geef een gestructureerd antwoord met:
1. Directe beantwoording van de vraag
2. Relevante wettelijke grondslag
3. Toepasselijke jurisprudentie
4. Praktische implicaties

Vermeld altijd de specifieke bronnen in je antwoord."""

        # Generate response using LlamaIndex LLM
        response = llm.complete(prompt)
        
        return json.dumps({
            "success": True,
            "data": response.text,
            "metadata": {
                "question": question, 
                "sources_used": len(sources_data.get('legislation', [])) + len(sources_data.get('case_law', [])),
                "framework": "LlamaIndex",
                "synthesis_method": "LlamaIndex response synthesis"
            }
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "data": None,
            "framework": "LlamaIndex"
        }, ensure_ascii=False)


# Create LlamaIndex FunctionTool
answer_tool = FunctionTool.from_defaults(
    fn=generate_answer_impl,
    name="generate_answer",
    description="Generate comprehensive tax answer based on legislation and case law sources using LlamaIndex response synthesis."
)