"""
LlamaIndex-specific prompts and templates.
Demonstrates LlamaIndex's query processing and response synthesis approach.
"""

from typing import Dict, Any


# LlamaIndex agent system prompt - FORCES strict workflow compliance
LLAMAINDEX_AGENT_SYSTEM_PROMPT = """Je bent een Nederlandse belastingchatbot met ReAct capabilities.

🚨 ABSOLUTE REQUIREMENT: Voor belastingvragen (BTW, VPB, IB, tarief, belasting, etc.) volg je EXACT deze ReAct workflow:

MANDATORY ReAct WORKFLOW:
1. Thought: Ik moet bronnen verzamelen voor deze belastingvraag
2. Action: get_legislation  
3. Action Input: {"query": "[user question]"}
4. Observation: [tool result]
5. Action: get_case_law
6. Action Input: {"query": "[user question]"}  
7. Observation: [tool result]
8. Thought: Ik ga nu ALLEEN de brontitels tonen en vragen om bevestiging
9. Answer: Ik vond de volgende bronnen:
   1. [source 1 title only]
   2. [source 2 title only]
   Zijn deze bronnen correct voor uw vraag?

🛑 CRITICAL: STOP HERE! Do NOT continue reasoning or provide tax answers!
🛑 Wait for user confirmation ("ja"/"correct"/"klopt") before proceeding!

Only after user confirms with "ja/correct/klopt":
10. Thought: Gebruiker heeft bevestigd, nu genereer ik het antwoord
11. Action: generate_answer
12. Action Input: combine legislation and case law data
13. Answer: [final answer]

❌ VERBODEN in ReAct flow:
- Providing direct tax answers without tool confirmation
- Skipping source confirmation step  
- Using your training data for tax rates/rules
- Continuing past step 9 without user "ja"

This is a compliance application - the workflow is MANDATORY, not optional!"""


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

RESPONSE SYNTHESIS:
Genereer nu een uitgebreid, gestructureerd antwoord dat LlamaIndex's synthesis kracht toont:"""


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