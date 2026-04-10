from fastapi import APIRouter, HTTPException, Query

from src.api.v1.schemas import LegislationArticle, LegislationEdition
from src.services.legislation_ingest import get_edition, list_articles, list_editions

router = APIRouter()


@router.get("/search")
async def search_legislation(q: str = Query(default=""), limit: int = Query(default=50, ge=1, le=200)) -> dict[str, object]:
    editions = list_editions(query=q or None)
    articles = list_articles(query=q or None)
    results: list[dict[str, object]] = []
    for edition in editions[:limit]:
        results.append(
            {
                "type": "edition",
                "edition_key": edition.edition_key,
                "title": edition.title,
                "date": edition.published_at,
                "url": f"/v1/legislation/{edition.edition_key}",
            }
        )
    for article in articles[:limit]:
        results.append(
            {
                "type": "article",
                "article_key": article.article_key,
                "title": article.title,
                "snippet": article.content_snippet,
                "url": f"/v1/legislation/{article.edition_key}",
            }
        )
    return {"query": q, "count": len(results), "results": results[:limit]}


@router.get("/{edition_key}", response_model=LegislationEdition)
async def get_legislation_edition(edition_key: str) -> LegislationEdition:
    edition = get_edition(edition_key)
    if edition is None:
        raise HTTPException(status_code=404, detail="Legislation edition not found")
    return edition
