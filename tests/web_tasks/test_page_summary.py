import unittest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup
import requests


from src.web_tasks.page_summary import WebsiteContentSummarizer


class TestWebsiteContentSummarizer(unittest.TestCase):

    def setUp(self):
        self.mock_openai = MagicMock()
        self.summarizer = WebsiteContentSummarizer(
                                                    url="https://example.com",
                                                    openai_instance=self.mock_openai,
                                                    openai_model="test-model",
                                                    explore_multiple_links=False,
                                                    verbosity=False,
                                                    truncate_total_webtext=1000
                                                )
        
    @patch("src.web_tasks.page_summary.requests.get")
    def test_get_soup_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"<html><head><title>Test</title></head><body>Hello</body></html>"
        soup = self.summarizer._get_soup("https://example.com")
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertEqual(soup.title.string, "Test")
        self.assertEqual(soup.body.string, "Hello")

    @patch("src.web_tasks.page_summary.requests.get")
    def test_get_soup_failure(self, mock_get):
        mock_get.side_effect = requests.RequestException("BoomBadaBoom!")
        soup = self.summarizer._get_soup("https://example.com")
        self.assertIsNone(soup)

    def test_prepare_user_prompt(self):
        result = self.summarizer._prepare_user_prompt("Summarize", "Site title", "Site content.")
        self.assertIn("Summarize", result)
        self.assertIn("Site title", result)
        self.assertIn("Site content", result)

    def test_build_prompt_messages(self):
        result = self.summarizer._build_prompt_messages("System prompt", "User prompt", "Test Title", "Test Content")
        self.assertEqual(len(result), 2)
        self.assertEqual("System prompt", result[0]["content"])
        self.assertEqual("You are looking at a website titled 'Test Title'.\n\nUser prompt\n\nTest Content", 
                         result[1]["content"])
        
    @patch.object(WebsiteContentSummarizer, "_load_content")
    def test_summarize_success(self, mock_load):
        mock_load.return_value = ("Site title", "Site content")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Summary result"))]
        self.mock_openai.chat.completions.create.return_value = mock_response
        result = self.summarizer.summarize(("Sys Prompt", "User Prompt"))
        self.assertEqual(result, "Summary result")

    @patch.object(WebsiteContentSummarizer, "_load_content")
    def test_summarize_failure_none_in_body(self, mock_load):
        mock_load.return_value = ("Site title", None)
        result = self.summarizer.summarize(("Sys Prompt", "User Prompt"))
        self.assertEqual("Unable to summarise because the website content could not be retrieved.", result)

    @patch.object(WebsiteContentSummarizer, "_load_content")
    def test_summarize_failure_failed_to_fetch_in_text(self, mock_load):
        mock_load.return_value = ("Site title", "Failed to fetch")
        result = self.summarizer.summarize(("Sys Prompt", "User Prompt"))
        self.assertEqual("Unable to summarise because the website content could not be retrieved.", result)

    @patch.object(WebsiteContentSummarizer, "_get_soup")
    def test_extract_text_from_single_link(self, mock_get_soup):
        html = "<html><head><title>Sample Page</title></head><body><p>Content</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        mock_get_soup.return_value = soup
        title, content = self.summarizer._extract_text_from_single_link("https://example.com")
        self.assertEqual(title, "Sample Page")
        self.assertIn("Content", content)

    @patch.object(WebsiteContentSummarizer, "_get_soup")
    def test_extract_text_from_single_link_failure(self, mock_get_soup):
        mock_get_soup.return_value = None
        title, content = self.summarizer._extract_text_from_single_link("https://example.com")
        self.assertEqual(title, "Failed to fetch content from https://example.com")
        self.assertIn("", content)



if __name__ == "__main__":
    unittest.main()