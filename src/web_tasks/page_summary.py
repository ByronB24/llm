from bs4 import BeautifulSoup
from typing import Dict, List, Tuple, Optional
import requests
from openai import OpenAI
from urllib.parse import urljoin
from .relevant_link_extractor import RelevantLinkExtractor
from rich.console import Console
from cachetools import LRUCache
from urllib.parse import urlparse
from src.logging import log_execution

class WebsiteContentSummarizer(RelevantLinkExtractor):
    """
    Fetches and summarizes the content of a single or multiple web pages using OpenAI's API.
    """

    HEADERS: Dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/117.0.0.0 Safari/537.36"),
        "Referer": "https://www.google.com/",
        
    }

    def __init__(self, url: str, openai_instance: OpenAI, openai_model: str, explore_multiple_links:bool = False, verbosity:bool = False, truncate_total_webtext:int = 5000):
        """
        Initializes the RecursiveWebsiteContentSummarizer.

        Parameters
        ----------
        url : str
            The URL of the website to summarize.
        openai_instance : OpenAI
            An initialized OpenAI API client.
        openai_model : str
            The name of the OpenAI model to use (e.g., 'gpt-3.5-turbo').
        explore_multiple_links : bool, optional
            Whether to extract and summarize linked pages (default is False).
        verbosity : bool, optional
            If True, enables detailed console logging (default is False).
        truncate_total_webtext : int, optional
            Maximum character limit for the extracted website text (default is 5000).

        Notes
        -----
        - This class extends `RelevantLinkExtractor` to filter relevant links using OpenAI.
        - Cached requests are stored using an LRU cache to optimize repeated requests.
        """
        super().__init__(openai_instance, openai_model)
        self.url: str = url
        self.openai_instance: OpenAI = openai_instance
        self.openai_model: str = openai_model
        self.explore_multiple_links:bool = explore_multiple_links
        self.truncate_total_webtext =truncate_total_webtext
        self.verbosity = verbosity
        if self.verbosity:
            self.console = Console()
        self._request_cache = LRUCache(maxsize=10) 
    

    def _log(self, message: str, description: str):
        self.console.print(f"{'='*20} {description} {'='*20}")
        self.console.print(message)



    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch and parse HTML content, using caching to avoid redundant requests.

        Parameters
        ----------
        url : str
            The webpage URL to fetch.

        Returns
        -------
        Optional[BeautifulSoup]
            Parsed BeautifulSoup object if the request is successful, otherwise None.
        """
        if url in self._request_cache:
            return self._request_cache[url]
        
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to fetch {url}: Status {response.status_code}")
                return None
            soup = BeautifulSoup(response.content, "html.parser")
            self._request_cache[url] = soup
            return soup
        except requests.RequestException as e:
            logger.exception(f"Error fetching website content from {url}")
            return None

    @log_execution("Relevant Links")
    def _extract_relevant_links(self,url:str, website_links:List[str]) -> List[Dict[str, str]]:
        """
        Extract relevant links using OpenAI-based filtering.

        Parameters
        ----------
        url : str
            The base website URL.
        website_links : List[str]
            List of extracted hyperlinks.

        Returns
        -------
        List[str]
            A filtered list of relevant hyperlinks.
        """
        return self.filter_links(url, website_links)

    def _extract_text_from_multiple_links(self,url:str)->Tuple[str, List[Dict[str, str]]]:
        """
        Extracts text from multiple linked pages.

        Parameters
        ----------
        url : str
            The base website URL.

        Returns
        -------
        Tuple[str, List[Dict[str, str]]]
            The main website title and a list of extracted content from relevant links.
        """

        #Extract the page title
        website_title, _  = self._extract_text_from_single_link(url)

        #Extract links
        website_links = self._extract_links(url)

        #Extract Relevant Links
        relevant_links = self._extract_relevant_links(url,website_links)       

        combined_website_text = []
        for link in relevant_links:

            page_title, page_text = self._extract_text_from_single_link(link['url'])
            combined_website_text.append({"type": link["type"], 
                                          "title":page_title,
                                          "content": page_text or "No content found."})
        
        return website_title, combined_website_text

    def _extract_text_from_single_link(self,url:str) -> Tuple[str, str]:
        """
        Extracts text content from a single webpage.

        Parameters
        ----------
        url : str
            The webpage URL.

        Returns
        -------
        Tuple[str, str]
            The extracted page title and content.
        """
        # Extract the page title
        soup = self._get_soup(url)

        if soup is None:
            return f"Failed to fetch content from {url}", ""

        if soup.title and soup.title.string:
            website_title = soup.title.string.strip()
        else:
            website_title = "No title found"

        # Remove unwanted elements
        for tag in soup(["script", "style", "img", "input"]):
            tag.extract()

        # Extract text from <body> (fallback to entire document if no <body>)
        if soup.body:
            body_text = soup.body.get_text(separator="\n", strip=True)
        else:
            body_text = soup.get_text(separator="\n", strip=True)

        #Normalise whitespace
        website_text = "\n".join(line.strip() for line in body_text.splitlines() if line.strip())

        
        return website_title, website_text
        
    @log_execution("Weblinks Extracted")
    def _extract_links(self,url)->List[str]:
        """
        Extracts valid hyperlinks from a webpage.

        Parameters
        ----------
        url : str
            The webpage URL.

        Returns
        -------
        List[str]
            A list of extracted hyperlinks.

        """
        soup = self._get_soup(url)
        if not soup:
            return []

        
        # Finds all <a> (anchor) elements with an href attribute.
        # Convert relative links (e.g., /about) to absolute URLs using urljoin().
        # Store links in a set to remove duplicates.
        links = {urljoin(url, a["href"]) for a in soup.find_all("a", href=True)}

        #  Filters only valid HTTP(S) links.
        valid_links = [link for link in links 
               if urlparse(link).scheme in {"http", "https"} and urlparse(link).netloc]


        return valid_links

    @log_execution("Title Page and Content Page/s")
    def _load_content(self) -> Tuple[str,str]:
        """
        Fetch and process the website content.

        """
        

        if self.explore_multiple_links:
            website_title, website_text = self._extract_text_from_multiple_links(self.url)
        else:
            website_title, website_text = self._extract_text_from_single_link(self.url)

        if self.truncate_total_webtext is not None:
            website_text = website_text[:self.truncate_total_webtext]

        return website_title, website_text


    @log_execution("User Prompt")
    def _prepare_user_prompt(self, user_prompt: str, website_title:str,website_text:str) -> str:
        """
        Constructs a formatted user prompt that includes the website title, user question, and website content.

        Parameters
        ----------
        user_prompt : str
            The user's initial question or instruction.
        website_title : str
            The extracted title of the website.
        website_text : str
            The cleaned text content of the website.

        Returns
        -------
        str
            A formatted string that provides context for the OpenAI model.
        """
        content = website_text if website_text else "No content available."
        return (
            f"You are looking at a website titled '{website_title}'.\n\n"
            f"{user_prompt}\n\n"
            f"{content}")

    def _build_prompt_messages(self, system_prompt: str, user_prompt: str, website_title:str, website_text:str)->List[Dict[str, str]]:
        """
        Construct the messages payload for OpenAI's API.

        Parameters
        ----------
        system_prompt : str
            The system-level instruction for the AI assistant.
        user_prompt : str
            The user's question or request.

        Returns
        -------
        list of dict
            A list of dictionaries in the format expected by OpenAI's chat-completion API.
        """
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._prepare_user_prompt(user_prompt, website_title, website_text)}]

    
    def summarize(self, summary_prompts:Tuple[str,str], links_filter_prompts:Tuple[str,str] = None ) -> str:
        """
        Summarize the website content using the OpenAI API.

        Parameters
        ----------
        summary_prompts : Tuple[str, str]
            The system and user prompt used for the summary in order : System, User.
        links_filter_prompts:Tuple[str,str], optional
           The system and user prompt used for the filtering links in order : System, User.

        Returns
        -------
        str
            The AI-generated summary or answer. Returns an error message on failure.
        """

        summary_system_prompt, summary_user_prompt = summary_prompts
        if links_filter_prompts is not None:
            self.links_filter_system_prompt, self.links_filter_user_prompt = links_filter_prompts 


        # Load and parse the website content
        website_title, website_text = self._load_content()

        # Check if content was successfully retrieved
        if not website_text or "Failed to fetch" in website_text:
            return "Unable to summarise because the website content could not be retrieved."
        
        try:
            response = self.openai_instance.chat.completions.create(
                model=self.openai_model,
                messages=self._build_prompt_messages(summary_system_prompt, summary_user_prompt, website_title, website_text)
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.exception("Error processing OpenAI API request.")
            return "Error generating summary."
