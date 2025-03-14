# GenAI Demo Repository

## **Introduction**
This repository serves as a collection of **demonstrations** showcasing **Generative AI (GenAI)** applications. 

The goal of this repository is to serve as an **educational and practical resource** for developers, researchers, and enthusiasts looking to dive into **GenAI**. 

---
### **Current Demos**
| Demo Name       | Description |
|----------------|------------|
| [Web Summary](#web-summary) | Extracts structured information from a website and generates a business report using GenAI. |

---

## **Demo: Web Summary**
### **Overview**
The **Web Summary** demo retrieves content from a website, processes it, and generates a structured **business report** using GenAI. It demonstrates how to:
1. **Fetch and clean webpage content** either from a single page, or links associated with a primary page provided.
2. **Engineer system and user prompts** to extract insights.
3. **Generate structured outputs** such as business summaries, target audience insights, and engagement analysis.


### **Requirements**
#### **System Requirements**
- Python **3.8+**
- A valid **OpenAI API key** (if using OpenAI models)
- .env file with API key must be in root
- Internet connection (for web scraping and API calls)

#### **Python Dependencies**
Install required dependencies using:
```bash
pip install -r requirements.txt