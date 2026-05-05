from fastapi.testclient import TestClient

from backend.app import app


client = TestClient(app)


def test_load_dataset_history_and_cards():
    resp = client.post("/api/datasets/load", json={"source": "maven"})
    assert resp.status_code == 200
    dataset = resp.json()
    assert dataset["dataset_id"]
    assert len(dataset["cards"]) >= 5

    history = client.get("/api/datasets")
    assert history.status_code == 200
    assert any(item["dataset_id"] == dataset["dataset_id"] for item in history.json())


def test_maven_and_gomask_card_capabilities():
    maven = client.post("/api/datasets/load", json={"source": "maven"}).json()
    gomask = client.post("/api/datasets/load", json={"source": "gomask"}).json()

    maven_cards = {card["key"]: card for card in maven["cards"]}
    gomask_cards = {card["key"]: card for card in gomask["cards"]}

    assert maven_cards["loss"]["enabled"] is True
    assert maven_cards["similar"]["enabled"] is False
    assert gomask_cards["loss"]["enabled"] is True
    assert gomask_cards["similar"]["enabled"] is True
    assert gomask_cards["actions"]["enabled"] is True


def test_dataset_scoped_missing_ids_return_404():
    assert client.get("/api/datasets/missing/metrics/summary").status_code == 404
    assert client.get("/api/datasets/missing/actions/summary").status_code == 404

    report = client.post("/api/datasets/missing/reports/ie-weekly", json={"period": "2024-W35"})
    assert report.status_code == 404

    search = client.post(
        "/api/datasets/missing/search",
        json={"query": "motor overheated", "top_k": 3, "use_reranker": False},
    )
    assert search.status_code == 404


def test_upload_csv_happy_path(tmp_path):
    csv = tmp_path / "upload.csv"
    csv.write_text(
        "Batch ID,Line,Product,Operator,Planned Minutes,Runtime Minutes,Downtime Minutes,Event ID,Downtime Reason,Note,Machine\n"
        "B1,L1,P1,O1,100,90,10,E1,Machine failure,Motor alarm,M1\n",
        encoding="utf-8",
    )

    with csv.open("rb") as f:
        resp = client.post("/api/datasets/upload", files={"file": ("upload.csv", f, "text/csv")})

    assert resp.status_code == 200
    dataset = resp.json()
    assert dataset["source"] == "upload"
    assert dataset["run_count"] == 1
    assert dataset["event_count"] == 1
