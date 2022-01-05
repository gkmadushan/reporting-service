from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from utils.database import Base
from dependencies import get_db, get_token_header


def override_get_token_header():
    return True


app.dependency_overrides[get_token_header] = override_get_token_header

client = TestClient(app)


def test_get_reports():
    response = client.get("/v1/reports")
    assert response.status_code == 200


def test_get_report_404():
    response = client.get("/v1/reports/c2fa95a2-ee1f-4910-b7be-ae3c81e91508")
    assert response.status_code == 404


def test_get_report_200():
    reports = response = client.get("/v1/reports")
    sample_id = reports.json()['data'][0]['id']
    response = client.get("/v1/reports/scans/{}".format(sample_id))
    assert response.status_code == 200
