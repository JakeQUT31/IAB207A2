from flask import Blueprint, render_template
from sqlalchemy.orm import joinedload
from .models import Event
from . import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    events = db.session.scalars(
        db.select(Event)
        .options(
            joinedload(Event.category),
            joinedload(Event.venue)
        )
        .order_by(Event.eventDate, Event.startTime)
    ).all()

    for event in events:
        event.playerBooked = Event.participantsBooked(event.eventID)
        event.spectatorBooked = Event.spectatorsBooked(event.eventID)

    return render_template('index.html', events=events)