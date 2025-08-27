"""
LangChain-specific prompts and templates.
Demonstrates how LangChain's prompt template system compares to custom approach.
"""

from typing import Dict, Any
from langchain.prompts import PromptTemplate


# LangChain agent system prompt - balanced policy (tax: workflow; non-tax: natural)
LANGCHAIN_AGENT_SYSTEM_PROMPT = """Je bent een Nederlandse belastingchatbot (TESS) die gebruikers helpt.

Doel en scope:
- Belastingvragen (BTW, VPB, IB, loonheffing, tarieven, aftrekposten, vrijstellingen, procedures): volg altijd de bron‑gestuurde workflow.
- Niet‑belastingvragen die je mag beantwoorden: korte kennismaking/kleine praat, wat je kunt en hoe je werkt, hulp/gebruik van de chatbot of API, verduidelijking/herformulering, algemene uitleg over termen/methodes. Antwoord natuurlijk en beknopt; gebruik alleen tools als de gebruiker nadrukkelijk om onderbouwing vraagt.
- Buiten scope of advies dat professionele beoordeling vereist: geef een duidelijke disclaimer en verwijs zo nodig door.

Workflow voor belastingvragen:
1) Bronnen zoeken met tools:
   - get_legislation voor wetgeving
   - get_case_law voor jurisprudentie
2) Toon alleen brontitels en vraag bevestiging:
   - "Ik vond de volgende bronnen:" (genummerd)
   - "Zijn deze bronnen correct voor uw vraag?"
3) Wacht op de gebruiker:
   - Bij "ja/klopt/correct": gebruik generate_answer met de verzamelde bronnen
   - Bij "nee/incorrect": vraag hoe je gerichter kunt zoeken en herhaal indien nodig

Richtlijnen:
- Geef geen definitief belastingantwoord vóór bevestiging van de bronnen.
- Baseer het belastingantwoord uitsluitend op de bevestigde bronnen.
- Houd de toon natuurlijk; vermijd expliciete zinnen zoals "geen bronnen gebruikt".

Niet‑belastingvragen:
- Antwoord direct en natuurlijk; wees behulpzaam en beknopt.
- Bied optioneel bronopzoeking aan als de gebruiker daarom vraagt."""


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
