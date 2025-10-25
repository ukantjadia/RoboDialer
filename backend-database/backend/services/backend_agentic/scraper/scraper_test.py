from scrapegraphai.graphs import SmartScraperGraph
import os
from dotenv import load_dotenv

load_dotenv()
deepseek_key = os.getenv("DEEPSEEK_API_KEY")
# Define the configuration for the scraping pipeline


graph_config = {
    "llm": {
        "model": "deepseek/deepseek-chat",
        "api_key": deepseek_key,
    },
    "verbose": True,
    "headless":True
}

#Using Ollama
'''graph_config = {
    "llm": {
        "model": "ollama/llama3.2",
        "model_tokens": 8192
    },
    "verbose": True,
    "headless": False,
}'''


# Create the SmartScraperGraph instance
smart_scraper_graph = SmartScraperGraph(
    prompt={
            "financial": "Extract financial information, revenue data, profit margins, growth rates, and any business metrics from this company website",
            "about": "Extract company information including mission, vision, history, founding details, and general company overview from this website",
            "team": "Extract information about company leadership, management team, founders, and key personnel from this website",
            "news": "Extract recent news, press releases, announcements, and company updates from this website",
            "products": "Extract information about products, services, solutions, and offerings from this company website",
            "general": "Extract comprehensive company information including business details, services, financial data, and key company facts from this website"
        },
    source="https://www.mmri-ny.com/",
    config=graph_config
)

# Run the pipeline
result = smart_scraper_graph.run()

import json
print(json.dumps(result, indent=4))