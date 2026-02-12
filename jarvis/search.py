import logging
import time

from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 5, retries: int = 2) -> str:
    clean_query = query.strip()
    if not clean_query:
        return "Search query is empty."

    for attempt in range(retries + 1):
        try:
            results = []
            with DDGS() as ddgs:
                for item in ddgs.text(clean_query, max_results=max_results):
                    title = item.get("title", "")
                    href = item.get("href", "")
                    body = item.get("body", "")
                    results.append(f"- {title}\n  {href}\n  {body}")
            if not results:
                return "No search results found."
            return "\n".join(results)
        except Exception as exc:
            logger.warning("Search failed (attempt %s): %s", attempt + 1, exc)
            if attempt < retries:
                time.sleep(0.4 * (attempt + 1))
    return "Search failed after retries."
