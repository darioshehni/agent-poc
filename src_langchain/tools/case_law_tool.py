"""
LangChain version of case law tool.
Demonstrates LangChain's tool decorator system.
"""

from langchain.tools import tool
import json


@tool
def get_case_law(query: str) -> str:
    """
    Retrieve relevant Dutch tax case law for a query.
    
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
        "metadata": {"query": query, "count": len(sample_case_law)}
    }, ensure_ascii=False)