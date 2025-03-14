import json
from openai import OpenAI
from typing import List, Dict
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s", 
    handlers=[
        logging.StreamHandler(), 
    ]
)

logger = logging.getLogger(__name__)

class RelevantLinkExtractor:
    """
    Use a GPT to determine which links are relevant for company brochure summarization.
    """

    def __init__(self, openai_instance: OpenAI, model: str):
        """
        Initializes the RelevantLinkExtractor.

        Parameters
        ----------
        openai_instance : OpenAI
            The OpenAI API client instance used for link filtering.
        model : str
            The name of the OpenAI model to use (e.g., 'gpt-4').

        Attributes
        ----------
        links_filter_system_prompt : Optional[str]
            The system-level prompt guiding link filtering (default is None).
        links_filter_user_prompt : Optional[str]
            The user-level prompt for filtering links based on relevance (default is None).

        Notes
        -----
        - This class utilizes GPT-based reasoning to determine which links are relevant.
        - It is meant to be extended by other classes.
        """


        self.openai_instance = openai_instance
        self.model = model
        self.links_filter_system_prompt = None
        self.links_filter_user_prompt = None

    def filter_links(self, base_url: str, links: List[str]) -> List[Dict[str, str]]:
        """
        Filters a list of hyperlinks based on relevance using GPT-based reasoning.

        Parameters
        ----------
        base_url : str
            The base website URL.
        links : List[str]
            A list of extracted hyperlinks.

        Returns
        -------
        List[Dict[str, str]]
            A list of dictionaries, each containing the relevant link and its type.
        """

        system_prompt = self.links_filter_system_prompt

        user_prompt = self.links_filter_user_prompt.format(url = base_url).join(links)


        response = self.openai_instance.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"}
        )

        try:
            return json.loads(response.choices[0].message.content)["links"]
        except Exception as e:
            logger.exception("Failed to parse GPT response for link filtering.")
            return []
