"""
LlamaIndex version of case law tool.
Demonstrates LlamaIndex's FunctionTool approach.
"""

from llama_index.core.tools import FunctionTool
import json


def get_case_law_impl(query: str) -> str:
    """
    Retrieve relevant Dutch tax case law for a query.
    Same hardcoded data as other implementations for fair comparison.
    
    Args:
        query: The tax question or topic to search case law for
        
    Returns:
        JSON string with case law results
    """
    # Same hardcoded response as original for fair comparison
    sample_case_law = [
        {
            "content": "ECLI:NL:HR:2020:123 - Hoge Raad uitspraak over btw-tarief op tandverzorgingsproducten",
            "source": "ECLI:NL:HR:2020:123",
            "court": "Hoge Raad",
            "year": "2020"
        },
        {
            "content": "ECLI:NL:RBAMS:2019:456 - Rechtbank Amsterdam over deelnemingsvrijstelling",
            "source": "ECLI:NL:RBAMS:2019:456", 
            "court": "Rechtbank Amsterdam",
            "year": "2019"
        }
    ]
    
    return json.dumps({
        "success": True,
        "data": sample_case_law,
        "metadata": {
            "query": query, 
            "count": len(sample_case_law),
            "framework": "LlamaIndex"
        }
    }, ensure_ascii=False)


# Create LlamaIndex FunctionTool
case_law_tool = FunctionTool.from_defaults(
    fn=get_case_law_impl,
    name="get_case_law", 
    description="Retrieve relevant Dutch tax case law and jurisprudence for a query. Provides structured legal precedents with court information."
)