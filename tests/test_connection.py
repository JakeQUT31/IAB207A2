import pytest
import requests
from website import create_app


def test_connection():
    app = create_app()
    client = app.test_client()
    
    response = client.get("/")
    assert response.status_code == 200