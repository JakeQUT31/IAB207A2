import pytest
import requests
from website import create_app


def test_eventDetailsConnection():
    app = create_app()
    client = app.test_client()
    
    response = client.get("/events/1")
    assert response.status_code == 200