"""
LlamaIndex version of legislation tool.
Demonstrates LlamaIndex's function tool approach and query processing.
"""

from llama_index.core.tools import FunctionTool
import json


def get_legislation_impl(query: str) -> str:
    """
    Retrieve relevant Dutch tax legislation for a query.
    Same hardcoded data as other implementations for fair comparison.
    
    Args:
        query: The tax question or topic to search legislation for
        
    Returns:
        JSON string with legislation results
    """
    # Same hardcoded response as original for fair comparison
    sample_legislation = [
        {
            "content": "Wet op de vennootschapsbelasting 1969, artikel 13: De deelnemingsvrijstelling is een belangrijke fiscale regeling in de Nederlandse vennootschapsbelasting. Kort gezegd betekent het dat een bedrijf (bijvoorbeeld een BV of NV) geen belasting hoeft te betalen over winst (dividenden of verkoopwinsten) die het ontvangt uit een kwalificerende deelneming.",
            "source": "Wet op de vennootschapsbelasting 1969, artikel 13",
            "article": "artikel 13",
            "law": "Wet VPB"
        },
        {
            "content": "Wet op de omzetbelasting 1968, artikel 2: het btw-tarief op goederen is 21%",
            "source": "Wet op de omzetbelasting 1968, artikel 2", 
            "article": "artikel 2",
            "law": "Wet OB"
        }
    ]
    
    return json.dumps({
        "success": True,
        "data": sample_legislation,
        "metadata": {
            "query": query, 
            "count": len(sample_legislation),
            "framework": "LlamaIndex"
        }
    }, ensure_ascii=False)


# Create LlamaIndex FunctionTool
legislation_tool = FunctionTool.from_defaults(
    fn=get_legislation_impl,
    name="get_legislation",
    description="Retrieve relevant Dutch tax legislation for a query. Provides structured legal sources with articles and content."
)