import logging
import time
from typing import List, Dict, Any
from urllib.parse import urlparse

from tavily import TavilyClient

from models import Claim
from config import TAVILY_API_KEY

logger = logging.getLogger(__name__)

client = TavilyClient(api_key=TAVILY_API_KEY)

SEARCH_QUERIES_TEMPLATE = [
    "{claim}",
    "{claim} latest statistics",
    "{claim} official source",
    "{claim} fact check",
]


def build_queries(claim_text: str) -> List[str]:
    """
    Generate multiple search query variations
    for better evidence retrieval.
    """
    return [
        template.format(claim=claim_text)
        for template in SEARCH_QUERIES_TEMPLATE
    ]


def search_claim(
    claim: Claim,
    max_retries: int = 3,
) -> List[Dict[str, Any]]:
    """
    Search the web for evidence related to a claim.

    Returns:
        List of source dictionaries:
        - title
        - url
        - domain
        - snippet
        - raw_content
        - published_date
    """

    # Use claim only (context often pollutes search quality)
    queries = build_queries(claim.text)

    seen_urls: set[str] = set()
    results: List[Dict[str, Any]] = []

    for query in queries:

        if len(results) >= 5:
            break

        for attempt in range(max_retries):

            try:
                response = client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5,
                    include_raw_content=True,
                )

                search_results = response.get("results")

                if not isinstance(search_results, list):
                    logger.warning(
                        "Unexpected Tavily response format"
                    )
                    search_results = []

                for result in search_results:

                    url = result.get("url", "").strip()

                    if not url or url in seen_urls:
                        continue

                    seen_urls.add(url)

                    try:
                        domain = urlparse(url).netloc
                    except Exception:
                        domain = ""

                    results.append(
                        {
                            "title": result.get(
                                "title",
                                "",
                            ).strip(),
                            "url": url,
                            "domain": domain,
                            "snippet": result.get(
                                "content",
                                "",
                            ).strip(),

                            # Reduced to save Claude tokens
                            "raw_content": result.get(
                                "raw_content",
                                "",
                            )[:2500],

                            "published_date": result.get(
                                "published_date"
                            ),
                        }
                    )

                    if len(results) >= 5:
                        break

                break

            except Exception as e:

                error_text = str(e).lower()

                if (
                    "rate limit" in error_text
                    or "429" in error_text
                ):
                    wait_time = 2 ** attempt

                    logger.warning(
                        "Rate limited. Retrying in %s seconds...",
                        wait_time,
                    )

                    time.sleep(wait_time)

                elif attempt < max_retries - 1:

                    logger.warning(
                        "Search attempt %s failed: %s",
                        attempt + 1,
                        e,
                    )

                    time.sleep(1)

                else:

                    logger.error(
                        "Search failed for query '%s': %s",
                        query,
                        e,
                    )

        # Small delay between query variations
        time.sleep(0.3)

    logger.info(
        "Found %s sources for claim: %s",
        len(results),
        claim.text[:60],
    )

    return results[:5]
