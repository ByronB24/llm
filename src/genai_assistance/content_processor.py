from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from openai import AsyncOpenAI
import json
import asyncio

@dataclass
class BusinessListing:
    """
    Represents a business listing with raw and processed content.

    Attributes
    ----------
    raw_content : str
        The original, unprocessed content scraped from the listing.
    name : str
        The name of the business.
    url : str
        The URL where the listing was found.
    cleaned_content : str
        The listing content after irrelevant data has been removed.
    extracted_info : Dict
        The structured information extracted from the listing content.
    """
    raw_content: str
    name: str
    url: str
    cleaned_content: str = ""
    extracted_info: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """
        Converts the business listing into a dictionary format.

        Returns
        -------
        dict
            Dictionary containing all attributes of the listing.
        """
        return {
            "name": self.name,
            "url": self.url,
            "raw_content": self.raw_content,
            "cleaned_content": self.cleaned_content,
            "extracted_info": self.extracted_info
        }

class GenAIBusinessListingProcessor:
    """
    Asynchronous processor for cleaning and extracting information from business listings using OpenAI.
    """
    
    def __init__(self,
                 cleaning_prompts: Tuple[str, str],
                 extraction_prompts: Tuple[str, str],
                 openai_instance: AsyncOpenAI,
                 openai_model: str,
                 concurrency_limit:int = 10) -> None:

        """
        Initialise the GenAIBusinessListingProcessor.

        Parameters
        ----------
        cleaning_prompts : Tuple[str, str]
            A tuple containing the system and user prompt for cleaning raw business listing content.
        extraction_prompts : Tuple[str, str]
            A tuple containing the system and user prompt for extracting structured information.
        openai_instance : OpenAI
            An authenticated instance of the OpenAI client.
        openai_model : str
            The name of the OpenAI model to use (e.g., "gpt-4", "gpt-3.5-turbo").
        concurrency_limit : int, optional
            Maximum number of concurrent API calls to the OpenAI client (default is 10).
        """
        
        self.cleaning_prompts = cleaning_prompts
        self.extraction_prompts = extraction_prompts
        self.openai = openai_instance
        self.model = openai_model
        self.semaphore = asyncio.Semaphore(concurrency_limit)
  
    async  def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Sends a prompt to the OpenAI model and returns the response content.

        Parameters
        ----------
        system_prompt : str
            System-level instruction for the model.
        user_prompt : str
            User-specific input for the model.

        Returns
        -------
        str
            The text content of the LLM response.
        """

        response = await self.openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content.strip()

    async def _clean_listing(self, listing: BusinessListing) -> BusinessListing:
        """
        Cleans raw content in the listing using LLM.

        Parameters
        ----------
        listing : BusinessListing
            Listing object with raw content.

        Returns
        -------
        BusinessListing
            Listing object with `cleaned_content` populated.
        """
        system_prompt = self.cleaning_prompts[0]
        user_prompt = self.cleaning_prompts[1].format(content=listing.raw_content)
        cleaned_text = await self._call_llm(system_prompt, user_prompt)
        listing.cleaned_content = cleaned_text
        return listing

    async  def _extract_info(self, listing: BusinessListing) -> BusinessListing:
        """
        Extracts structured info from cleaned content using LLM.

        Parameters
        ----------
        listing : BusinessListing
            Listing object with cleaned content.

        Returns
        -------
        BusinessListing
            Listing object with `extracted_info` populated.
        """
        system_prompt = self.extraction_prompts[0]
        user_prompt = self.extraction_prompts[1].format(content=listing.cleaned_content) #You might want to truncate content to minimise cost
        extracted_json = await self._call_llm(system_prompt, user_prompt) #You might want to truncate content to minimise cost
        try:
            listing.extracted_info = json.loads(extracted_json)
        except json.JSONDecodeError:
            listing.extracted_info = {"error": "Failed to parse JSON"}
        return listing

    async def _process_single_listing(self, listing: BusinessListing) -> BusinessListing:
        """
        Orchestrates cleaning and info extraction for a single listing with concurrency control.

        Parameters
        ----------
        listing : BusinessListing
            A single business listing object.

        Returns
        -------
        BusinessListing
            Fully processed listing with cleaned and extracted info.
        """
        await self._clean_listing(listing)
        await self._extract_info(listing)
        return listing
        
    async def _process_single_listing(self, listing: BusinessListing) -> BusinessListing:
        """
        Orchestrates cleaning and info extraction for a single listing with concurrency control.

        Parameters
        ----------
        listing : BusinessListing
            A single business listing object.

        Returns
        -------
        BusinessListing
            Fully processed listing with cleaned and extracted info.
        """

        async with self.semaphore:
            await self._clean_listing(listing)
            await self._extract_info(listing)
            return listing

    async def process_listings(self, raw_listings: List[Dict[str, str]]) -> List[Dict]:
        """
        Processes a list of raw listings by cleaning and extracting structured info.

        Parameters
        ----------
        raw_listings : List[Dict[str, str]]
            List of dictionaries containing 'name', 'content', and 'url' for each listing.

        Returns
        -------
        List[Dict]
            List of processed listings in dictionary format.
        """
        listings = [BusinessListing(name=item["name"], raw_content=item["content"], url=item["url"]) for item in raw_listings]
        tasks = [self._process_single_listing(l) for l in listings]
        results = await asyncio.gather(*tasks)
        return [l.to_dict() for l in results]


