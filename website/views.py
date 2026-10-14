from flask import Blueprint, render_template, request
from sqlalchemy.orm import joinedload

from .models import Event
from . import db
from .search_utils import semantic_search


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    search = request.args.get("q", "").strip()

    query = (
        db.select(Event)
        .options(
            joinedload(Event.category),
            joinedload(Event.venue),
        )
        .order_by(Event.eventDate, Event.startTime)
    )

    if search:
        # First try normal keyword search on the event title
        keyword_results = db.session.scalars(
            query.where(Event.title.ilike(f"%{search}%"))
        ).all()

        if keyword_results:
            events = keyword_results

        else:
            # No title match, so use AI semantic search
            all_events = db.session.scalars(query).all()

            search_lower = search.lower()

            sport_names = [
                "touch football",
                "football",
                "cricket",
                "basketball",
                "netball",
                "tennis",
                "afl",
            ]

            requested_sport = next(
                (
                    sport
                    for sport in sport_names
                    if sport in search_lower
                ),
                None,
            )

            # If the user names a sport, only search that sport
            if requested_sport:
                candidates = [
                    event
                    for event in all_events
                    if event.category
                    and event.category.categoryName.lower() == requested_sport
                ]
            else:
                candidates = all_events

            if candidates:
                semantic_results = semantic_search(
                    search,
                    candidates,
                )

                events = [
                    event
                    for event, similarity in semantic_results
                ]
            else:
                events = []

    else:
        events = db.session.scalars(query).all()

    # Booking counts used by the event cards
    for event in events:
        event.playerBooked = Event.participantsBooked(event.eventID)
        event.spectatorBooked = Event.spectatorsBooked(event.eventID)

    return render_template(
        "index.html",
        events=events,
        search=search,
    )