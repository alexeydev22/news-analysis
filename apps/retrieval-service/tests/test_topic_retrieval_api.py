from fastapi.testclient import TestClient
from retrieval_service.main.app import create_app


def test_list_documents_endpoint_returns_indexed_documents() -> None:
    with TestClient(create_app(use_fake_components=True)) as client:
        response = client.get("/api/v1/documents?limit=2")

    assert response.status_code == 200
    assert response.json() == {
        "documents": [
            {
                "id": "news-1",
                "title": "GDP grows",
                "text": "GDP grew by 2 percent.",
                "source": "demo",
                "published_at": None,
                "metadata": {},
            },
        ],
    }


def test_neighbors_endpoint_returns_groups() -> None:
    with TestClient(create_app(use_fake_components=True)) as client:
        response = client.post(
            "/api/v1/neighbors",
            json={"document_ids": ["news-1"], "limit": 2},
        )

    assert response.status_code == 200
    assert response.json() == {
        "groups": [
            {
                "document_id": "news-1",
                "neighbors": [
                    {
                        "id": "news-2",
                        "score": 0.86,
                        "title": "GDP outlook improves",
                        "text": "Analysts upgraded GDP outlook.",
                        "source": "demo",
                        "published_at": None,
                        "metadata": {},
                    },
                ],
            },
        ],
    }
