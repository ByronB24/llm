import logging
import re
from bs4 import BeautifulSoup
from typing import Dict, Optional
import requests
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebsiteContentSummarizer:
    """
    Fetches and summarizes the content of a single web page using OpenAI's API.

    Attributes
    ----------
    url : str
        The URL of the website to be summarized.
    openai_instance : OpenAI
        The OpenAI API client instance.
    openai_model : str
        The name of the OpenAI model to use (e.g., 'gpt-3.5-turbo').
    HEADERS : Dict[str, str]
        A dictionary of HTTP headers used for the request.
    website_title : str
        The extracted title of the website.
    website_text : Optional[str]
        The main text content of the website, after cleaning.
    """

    HEADERS: Dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/117.0.0.0 Safari/537.36"
        )
    }

    def __init__(self, url: str, openai_instance: OpenAI, openai_model: str):
        """
        Initialize the WebsiteContentSummarizer.

        Parameters
        ----------
        url : str
            The URL of the website to summarize.
        openai_instance : OpenAI
            An initialized OpenAI API client.
        openai_model : str
            The name of the OpenAI model to use.
        """
        self.url: str = url
        self.openai_instance: OpenAI = openai_instance
        self.openai_model: str = openai_model
        self.website_title: str = "No title found"
        self.website_text: Optional[str] = None

    def _load_content(self) -> None:
        """
        Fetch and process the website content.

        Notes
        -----
        This method:
        1. Retrieves the website content using `requests.get`.
        2. Raises an HTTPError if the request fails (4xx or 5xx).
        3. Uses BeautifulSoup to parse the HTML content.
        4. Removes unwanted elements (scripts, styles, images, inputs).
        5. Extracts the page title and text into `website_title` and `website_text`.
        """
        try:
            response = requests.get(self.url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract the page title
            if soup.title and soup.title.string:
                self.website_title = soup.title.string.strip()

            # Remove unwanted elements
            for tag in soup.select("script, style, img, input"):
                tag.decompose()

            # Extract text from <body> (fallback to entire document if no <body>)
            if soup.body:
                body_text = soup.body.get_text(separator="\n", strip=True)
            else:
                body_text = soup.get_text(separator="\n", strip=True)

            # Normalize whitespace (optional but improves readability)
            self.website_text = re.sub(r'\n+', '\n', body_text).strip()

        except requests.RequestException as e:
            logger.exception("Error fetching website content from %s", self.url)
            self.website_text = "Failed to fetch website content."

    def _prepare_user_prompt(self, user_prompt: str) -> str:
        """
        Prepare the user prompt with minor adjustments.

        Parameters
        ----------
        user_prompt : str
            The user's initial question or instruction.

        Returns
        -------
        str
            A string that includes the website title, user prompt, and website text.
        """
        content = self.website_text if self.website_text else "No content available."
        return (
            f"You are looking at a website titled '{self.website_title}'.\n\n"
            f"{user_prompt}\n\n"
            f"{content}"
        )

    def _build_prompt_messages(self, system_prompt: str, user_prompt: str):
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
            {"role": "user", "content": self._prepare_user_prompt(user_prompt)}
        ]

    def summarize(self, system_prompt: str, user_prompt: str) -> str:
        """
        Summarize the website content using the OpenAI API.

        Parameters
        ----------
        system_prompt : str
            The system-level prompt guiding the style or behavior of the AI.
        user_prompt : str
            The user-level prompt or question about the website content.

        Returns
        -------
        str
            The AI-generated summary or answer. Returns an error message on failure.
        """
        # Load and parse the website content
        self._load_content()

        # Check if content was successfully retrieved
        if not self.website_text or "Failed to fetch" in self.website_text:
            return "Unable to summarize because the website content could not be retrieved."

        try:
            response = self.openai_instance.chat.completions.create(
                model=self.openai_model,
                messages=self._build_prompt_messages(system_prompt, user_prompt)
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.exception("Error processing OpenAI API request.")
            return "Error generating summary."
