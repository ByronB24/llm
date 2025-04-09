from llama_index.core.schema import Document
from typing import Dict, Any
import json 

def llamaindex_format_doc(listing:Dict[str, Any])->Document:
    """
    Converts a business listing dictionary into a LlamaIndex Document object.

    Parameters
    ----------
    listing : dict
        A dictionary containing business listing information. Must contain at least
        'cleaned_content', 'extracted_info', 'name', and 'url'.

    Returns
    -------
    Document
        A Document object with structured page content and metadata for indexing.
    """
    return Document(

        page_content= (
                        f"Listing Content:\n{listing['cleaned_content']}\n\n"
                        f"Structured Summary:\n{json.dumps(listing['extracted_info'], indent=2)}"
                        ),

        metadata={
            **listing['extracted_info'], 
            "title": listing["name"],
            "url": listing["url"],
        }
    )

