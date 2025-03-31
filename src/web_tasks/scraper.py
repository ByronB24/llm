from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import os
from typing import Optional, List, Dict, Any
from src.selenium import with_driver, ChromeDriverMixin


class BusinessListingScraper(ChromeDriverMixin):
    """
    A scraper for extracting business listings and content from a paginated website.

    """
    def __init__(self, 
                 search_page_url: Optional[str] = None,
                 max_pages: int = 1,
                 stored_page_content_path: Optional[str] = None,
                 driver_path: Optional[str] = None,
                 output_save_path: Optional[str] = None,
                 )->None:
        """
        Initialise the BusinessListingScraper.

        Parameters
        ----------
        search_page_url : str, optional
            URL of the search results page to scrape listings from.
        max_pages : int, optional
            Maximum number of pages to scrape, by default 1.
        stored_page_content_path : str, optional
            Path to a JSON file containing previously scraped data.
        driver_path : str, optional
            File path to an existing ChromeDriver executable. If not provided, one will be downloaded.
        output_save_path : str, optional
            Directory path where the final output JSON file will be saved.

        Raises
        ------
        ValueError
            If neither `search_page_url` nor `stored_page_content_path` is provided.
        """

        if not search_page_url and not stored_page_content_path:
            raise ValueError("Either 'search_page' or 'stored_page_content_path' must be provided.")

        self.search_page = search_page_url
        self.stored_page_content_path = stored_page_content_path
        self.max_pages = max_pages
        self.output_save_path = output_save_path
        self.driver_path = driver_path or ChromeDriverManager().install()
        self.driver = None
    
    def _get_page_url(self, page:int) -> str:
        """
        Constructs a full URL for a given page index.

        Parameters
        ----------
        page : int
            The page number to construct the URL for.

        Returns
        -------
        str
            The constructed URL.
        """
        return f"{self.search_page}-{page}" if page > 1 else self.search_page

    def get_page_source(self, page: int = 1) -> str:
        """
        Loads and returns the HTML source of a given page.

        Parameters
        ----------
        page : int, optional
            The page number to load.

        Returns
        -------
        str
            The HTML content of the page.
        """
        url = self._get_page_url(page)
        self.driver.get(url)
        page_source = self.driver.page_source
        return page_source 

    def is_invalid_page(self, soup: BeautifulSoup) -> bool:
        """
        Detects whether a page is invalid (e.g., 404).

        Parameters
        ----------
        soup : BeautifulSoup
            Parsed HTML content.

        Returns
        -------
        bool
            True if page is invalid, False otherwise.
        """
        error_div = soup.find("div", class_="error-code")
        return error_div is not None and "HTTP ERROR 404" in error_div.get_text(strip=True)

    @with_driver
    def extract_listings_from_page(self, page: int = 1) -> Optional[List[Dict[str, Any]]]:
        """
        Extracts business listings from a given page.

        Parameters
        ----------
        page : int, optional
            The page number to scrape.

        Returns
        -------
        list of dict or None
            A list of listings with name, URL, and page number, or None if invalid.
        """

        html = self.get_page_source(page)
        soup = BeautifulSoup(html, "html.parser")

        if self.is_invalid_page(soup):
            print(f"[Info] Page {page} flagged as invalid by is_invalid_page().")
            return None

        listings = []

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string.strip())
                if isinstance(data, dict) and data.get("@type") == "ItemList":
                    for item in data.get("itemListElement", []):
                        if item.get("@type") == "ListItem":
                            listings.append({
                                "page": page,
                                "name": item.get("name"),
                                "url": item.get("url")
                            })
            except Exception:
                continue

        return listings
    
    def extract_all_listings(self) -> list:
        """
        Iteratively extracts listings across paginated results.

        Returns
        -------
        list of dict
            All listings from successfully parsed pages.
        """
        listings_result = []

        for page in range(1, self.max_pages + 1):
            print(f"[Page {page}] Extracting listings...")

            retries = 0
            max_retries = 5
            listings = None

            #If listing retrieval fails, try again n times
            while retries < max_retries:
                try:
                    listings = self.extract_listings_from_page(page)
                    if listings:
                        break  # breaks on great success!!
                except Exception as e:
                    print(f"[RETRY {retries + 1}] Failed to extract page {page}: {e}")
                retries += 1

            # Final fallback: reinstall ChromeDriver and try once more
            if not listings:
                print(f"[FINAL ATTEMPT] Reinstalling ChromeDriver and retrying page {page}...")
                
                self.driver_path = ChromeDriverManager().install()

                try:
                    listings = self.extract_listings_from_page(page)
                except Exception as e:
                    print(f"[FAILED FINAL ATTEMPT] Could not extract page {page} even after reinstalling driver: {e}")
                    break

            if listings is None or len(listings) == 0:
                print("No more valid listings or reached end of pages. Stopping.")
                print(self._get_page_url(page))
                break

            listings_result.extend(listings)

        return listings_result

    @with_driver
    def extract_listing_content(self, url: str) -> str:
        """
        Extracts visible text content from a single listing URL.

        Parameters
        ----------
        url : str
            The listing URL to scrape.

        Returns
        -------
        str
            The cleaned text content.
        """

        try:
            self.driver.get(url)
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Remove unwanted tags
            for tag in soup(["script", "style", "img", "svg", "nav", "footer", "input", "button"]):
                tag.decompose()

            content = soup.get_text(separator="\n", strip=True)
            return "\n".join(line.strip() for line in content.splitlines() if line.strip())

        except Exception as e:
            print(f"[ERROR] Failed to extract content from {url}: {e}")
            return ""


    def enrich_listings_with_content(self, listings: list) -> list:
        """
        Enriches listings with textual content from their URLs.

        Parameters
        ----------
        listings : list of dict
            Basic listing metadata.

        Returns
        -------
        list of dict
            Listings with added 'content' field.
        """
        enriched = []

        for idx, listing in enumerate(listings, start=1):
            print(f"[{idx}/{len(listings)}] Extracting content from: {listing['url']}")
            content = self.extract_listing_content(listing["url"])
            listing["content"] = content
            enriched.append(listing)

        return enriched

    def _load_from_json(self) -> List[Dict[str, Any]]:
        """
        Loads listings from a JSON file.

        Returns
        -------
        list of dict
            Listings loaded from disk.
        """
        if not os.path.exists(self.stored_page_content_path):
            raise FileNotFoundError(f"JSON file not found: {self.stored_page_content_path}")
        with open(self.stored_page_content_path, 'r') as f:
            return json.load(f)

    def extract_listings_and_page_content(self) -> List[Dict[str, Any]]:
        """
        Full pipeline to extract listings and their page content.

        Returns
        -------
        list of dict
            Fully enriched listings.
        """
        if self.stored_page_content_path:
            return self._load_from_json()
        else:
            listings = self.extract_all_listings()
            listing_and_content = self.enrich_listings_with_content(listings)

            if self.output_save_path:
                self._save_output(listing_and_content)

            return listing_and_content

    def _save_output(self, output: List[Dict[str, Any]]) -> None:
        """
        Saves enriched listings to a JSON file.

        Parameters
        ----------
        output : list of dict
            The listings to persist to disk.
        """
        os.makedirs(self.output_save_path, exist_ok=True)  
        file_path = os.path.join(self.output_save_path, "listings_output.json")

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=4, ensure_ascii=False)  
    
