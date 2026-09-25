import pytest
import requests
from website import models, db
from website.models import Event
from website import create_app

def test_databaseGather():
    app = create_app({"TESTING": True})
    with app.app_context():
        event = db.session.scalar(db.select(Event).where(Event.eventID==1))
        assert event.eventID == 1