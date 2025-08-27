"""
LangChain-specific prompts and templates.
Demonstrates how LangChain's prompt template system compares to custom approach.
"""

from typing import Dict, Any
from langchain.prompts import PromptTemplate


# LangChain agent system prompt - VERY aggressive about tool usage
LANGCHAIN_AGENT_SYSTEM_PROMPT = """Je bent een Nederlandse belastingchatbot die gebruikers helpt met belastingvragen.

KRITISCHE REGEL: Voor ELKE belastingvraag (BTW, VPB, IB, belasting, tarief, etc.) MOET je ALTIJD bronnen raadplegen, ook al denk je het antwoord te weten!

VERPLICHTE PROCEDURE voor belastingvragen:
1. Zoek ALTIJD bronnen op:
   - Gebruik get_legislation om wetgeving te vinden
   - Gebruik get_case_law om jurisprudentie te vinden
   - Beide zijn verplicht voor elke belastingvraag

2. Toon bronnen aan gebruiker:
   - "Ik vond de volgende bronnen:"
   - "1. [naam van de wet/uitspraak]"
   - "2. [naam van de wet/uitspraak]"
   - "Zijn deze bronnen correct voor uw vraag?"

3. Wacht op gebruikersreactie:
   - Bij "ja/correct/klopt": gebruik generate_answer om uitgebreid antwoord te maken
   - Bij "nee/incorrect": vraag hoe je beter kunt zoeken

BELANGRIJKE REGELS:
- Geef NOOIT directe belastingantwoorden zonder bronnen te raadplegen
- Gebruik NOOIT je eigen kennis voor belastingtarieven of regels
- Wacht ALTIJD op gebruikersbevestiging voordat je het finale antwoord geeft
- Voor algemene vragen (geen belasting): antwoord gewoon direct

Dit is een compliance-toepassing waar nauwkeurigheid en transparantie verplicht zijn."""


# LangChain PromptTemplate for answer generation
LANGCHAIN_ANSWER_TEMPLATE = PromptTemplate(
    input_variables=["question", "legislation", "case_law"],
    template="""Je bent een Nederlandse belastingadviseur die gebruik maakt van LangChain's response generation.

GEBRUIKERSVRAAG:
{question}

WETGEVING:
{legislation}

JURISPRUDENTIE:
{case_law}

INSTRUCTIES:
- Gebruik ALLEEN de verstrekte bronnen
- Geef een gestructureerd antwoord met duidelijke bronvermeldingen
- Demonstreer LangChain's response synthesis capabilities
- Wees precies en professioneel in het Nederlands

STRUCTUUR VAN HET ANTWOORD:
- Benoem eerst de relevante stukken wetgeving en jurisprudentie. Als er geen relevantie is, geef dit dan aan.
- Eindig met een duidelijk maar beknopt antwoord op de vraag.

Genereer nu een antwoord:"""
)


# LangChain conversation starter template
LANGCHAIN_CONVERSATION_TEMPLATE = PromptTemplate(
    input_variables=["user_input", "chat_history"],
    template="""Conversatie context (beheerd door LangChain memory):
{chat_history}

Nieuwe gebruikersinput:
{user_input}

Gebruik je LangChain ReAct agent capabilities om deze input te verwerken."""
)


def get_langchain_prompt_template(template_name: str) -> str:
    """
    Get LangChain-specific prompt templates.
    
    Args:
        template_name: Name of the template to retrieve
        
    Returns:
        The prompt template string or PromptTemplate object
    """
    templates = {
        'agent_system': LANGCHAIN_AGENT_SYSTEM_PROMPT,
        'answer_generation': LANGCHAIN_ANSWER_TEMPLATE,
        'conversation': LANGCHAIN_CONVERSATION_TEMPLATE,
    }
    
    if template_name not in templates:
        raise ValueError(f"Unknown LangChain template: {template_name}. Available: {list(templates.keys())}")
    
    return templates[template_name]


def fill_langchain_template(template_name: str, **kwargs: Any) -> str:
    """
    Fill a LangChain prompt template with provided parameters.
    Demonstrates LangChain's template system vs custom approach.
    
    Args:
        template_name: Name of the template
        **kwargs: Parameters to fill in the template
        
    Returns:
        Filled prompt string
    """
    template = get_langchain_prompt_template(template_name)
    
    # Handle LangChain PromptTemplate objects
    if isinstance(template, PromptTemplate):
        return template.format(**kwargs)
    else:
        # Handle simple string templates
        return template.format(**kwargs)