"""
LlamaIndex-specific prompts and templates.
Demonstrates LlamaIndex's query processing and response synthesis approach.
"""

from typing import Dict, Any


# LlamaIndex agent system prompt - FORCES strict workflow compliance
LLAMAINDEX_AGENT_SYSTEM_PROMPT = """Je bent een Nederlandse belastingchatbot die gebruikers helpt met belastingvragen.

🚨 ABSOLUTE VEREISTE: Voor belastingvragen (BTW, VPB, IB, tarief, belasting, etc.) moet je ALTIJD deze procedure volgen:

VERPLICHTE PROCEDURE:

1. Zoek bronnen op:
   - Gebruik get_legislation om relevante wetgeving te vinden
   - Gebruik get_case_law om relevante jurisprudentie te vinden
   - Beide zijn verplicht voor elke belastingvraag

2. Toon ALLEEN de brontitels aan gebruiker:
   "Ik vond de volgende bronnen:
   1. [titel van wet/artikel]
   2. [titel van uitspraak]
   Zijn deze bronnen correct voor uw vraag?"

3. STOP en wacht op gebruikersbevestiging:
   - Als gebruiker "ja/correct/klopt" zegt: gebruik generate_answer
   - Als gebruiker "nee/incorrect" zegt: vraag hoe je beter kunt zoeken

KRITIEKE REGELS:
- Geef NOOIT directe belastingantwoorden zonder bronnen te controleren
- Gebruik NOOIT je eigen kennis voor belastingtarieven of regels  
- Ga NOOIT door naar het finale antwoord zonder gebruikersbevestiging
- Voor niet-belastingvragen: antwoord direct

Dit is een compliance-toepassing waar de procedure strikt gevolgd moet worden."""


# LlamaIndex response synthesis template
LLAMAINDEX_SYNTHESIS_TEMPLATE = """Je bent een Nederlandse belastingadviseur die LlamaIndex's response synthesis gebruikt.

QUERY PROCESSING CONTEXT:
Oorspronkelijke vraag: {question}
Query transformatie resultaat: {transformed_query}

RETRIEVED SOURCES:
Wetgeving: {legislation}
Jurisprudentie: {case_law}

SYNTHESIS INSTRUCTIES:
- Gebruik LlamaIndex's response synthesis approach
- Combineer bronnen intelligent voor coherent antwoord
- Toon query processing benefits in het finale antwoord
- Geef gestructureerd antwoord met duidelijke bronvermeldingen
- Demonstreer information integration capabilities

STRUCTUUR VAN HET ANTWOORD:
- Leg eerst kort het verband tussen de vraag en de relevante bronnen uit. Als er geen relevantie is, geef dit dan aan.
- Eindig met een duidelijk maar beknopt antwoord op de vraag.

RESPONSE SYNTHESIS:
Genereer nu een antwoord:"""


# LlamaIndex query transformation template
LLAMAINDEX_QUERY_TEMPLATE = """LlamaIndex Query Processing voor Nederlandse belastingvragen.

ORIGINELE QUERY: {original_query}

QUERY ANALYSIS:
- Identificeer belastinggebied (BTW, IB, VPB, etc.)
- Extract key entities en concepten
- Determine required information sources
- Plan retrieval strategy

TRANSFORMED QUERY:
Herformuleer de query voor optimale source retrieval:"""


# LlamaIndex conversation context template  
LLAMAINDEX_CONTEXT_TEMPLATE = """LlamaIndex Chat Context Management:

CONVERSATION HISTORY (managed by ChatMemoryBuffer):
{chat_history}

CURRENT QUERY PROCESSING:
User Input: {user_input}
Query Stage: {processing_stage}
Retrieved Context: {context}

NEXT ACTIONS:
{next_actions}"""


def get_llamaindex_prompt_template(template_name: str) -> str:
    """
    Get LlamaIndex-specific prompt templates.
    
    Args:
        template_name: Name of the template to retrieve
        
    Returns:
        The prompt template string
    """
    templates = {
        'agent_system': LLAMAINDEX_AGENT_SYSTEM_PROMPT,
        'response_synthesis': LLAMAINDEX_SYNTHESIS_TEMPLATE,
        'query_transformation': LLAMAINDEX_QUERY_TEMPLATE,
        'conversation_context': LLAMAINDEX_CONTEXT_TEMPLATE,
    }
    
    if template_name not in templates:
        raise ValueError(f"Unknown LlamaIndex template: {template_name}. Available: {list(templates.keys())}")
    
    return templates[template_name]


def fill_llamaindex_template(template_name: str, **kwargs: Any) -> str:
    """
    Fill a LlamaIndex prompt template with provided parameters.
    Demonstrates LlamaIndex's approach to query processing and synthesis.
    
    Args:
        template_name: Name of the template
        **kwargs: Parameters to fill in the template
        
    Returns:
        Filled prompt string
    """
    template = get_llamaindex_prompt_template(template_name)
    
    try:
        return template.format(**kwargs)
    except KeyError as e:
        raise KeyError(f"Missing required parameter for LlamaIndex template {template_name}: {e}")


def transform_query_for_retrieval(original_query: str) -> str:
    """
    Transform user query for better source retrieval.
    Demonstrates LlamaIndex's query processing capabilities.
    
    Args:
        original_query: Original user question
        
    Returns:
        Transformed query optimized for retrieval
    """
    # Simple query transformation example
    # In real LlamaIndex usage, this would be more sophisticated
    
    query_lower = original_query.lower()
    
    # Add tax context if not present
    if not any(term in query_lower for term in ['btw', 'belasting', 'tax', 'wet', 'artikel']):
        transformed = f"Nederlandse belasting: {original_query}"
    else:
        transformed = original_query
    
    # Expand common abbreviations
    transformations = {
        'btw': 'btw omzetbelasting',
        'vpb': 'vennootschapsbelasting',
        'ib': 'inkomstenbelasting'
    }
    
    for abbrev, expansion in transformations.items():
        if abbrev in query_lower:
            transformed = transformed.replace(abbrev, expansion)
    
    return transformed