import unittest
from unittest.mock import MagicMock, patch
from src.web_tasks.relevant_link_extractor import RelevantLinkExtractor
import json

class TestRelevantLinkExtractor(unittest.TestCase):

    def setUp(self):
        self.mock_openai = MagicMock()
        self.extractor = RelevantLinkExtractor(
                                                openai_instance=self.mock_openai,
                                                model="test-model")
        self.extractor.links_filter_system_prompt = "System prompt"
        self.extractor.links_filter_user_prompt = "User prompt"
        self.about_page = "https://example.com/about"
        self.services_page = "https://example.com/services"
        self.example_site = "https://example.com"

    def test_filter_links_success(self):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "links": [
                    {"type": "about", "url": self.about_page},
                    {"type": "services", "url": self.services_page}
                ]
            })))
        ]
        self.mock_openai.chat.completions.create.return_value = mock_response

        base_url = self.example_site
        links = [self.about_page, self.services_page]
        result = self.extractor.filter_links(base_url, links)

        print(result)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["url"], self.about_page)
        self.assertEqual(result[1]["url"], self.services_page)



if __name__ == "__main__":
    unittest.main()
