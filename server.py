from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from readme_generator import get_readme

app = FastAPI(title="README Generator", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/readme")
def readme_endpoint(
    url: str = Query(..., description="URL репозитория на GitHub"),
    token: str | None = Query(None, description="GitHub token (опционально)"),
):
    try:
        content = get_readme(url, token=token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if content.startswith("Ошибка"):
        raise HTTPException(status_code=500, detail=content)

    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="README.md"'},
    )
