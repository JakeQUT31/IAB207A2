from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from .models import Event, Venue
from . import db
from .forms import CustodianForm
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
    status_changed = False

    for event in events:
        old_status = event.status
        event.updateStatus()

        status_changed = status_changed or event.status != old_status

        event.playerBooked = Event.participantsBooked(event.eventID)
        event.spectatorBooked = Event.spectatorsBooked(event.eventID)

    if status_changed:
        db.session.commit()

    featured_event = next(
        (
            event
            for event in events
            if event.status not in ["Inactive", "Cancelled"]
        ),
        None,
    )

    return render_template(
        "index.html",
        events=events,
        search=search,
        featured_event=featured_event,
    )


@main_bp.route("/acknowledgement", methods=["GET", "POST"])
def acknowledgement():
    form = CustodianForm()

    if form.validate_on_submit():
        suburb = form.custodianSearch.data

        checkKnown = db.session.scalar(
            db.select(func.count(Venue.venueID))
            .select_from(Venue)
            .where(
                (Venue.suburb == suburb),
                (Venue.traditionalCustodians != "Not Specified"),
            )
        )

        if checkKnown > 0:
            known = db.session.scalar(
                db.select(Venue.traditionalCustodians)
                .where(
                    (Venue.suburb == suburb),
                    (Venue.traditionalCustodians != "Not Specified"),
                )
            )

            flash(f"Traditional Owners: {known}!", "success")
        else:
            flash("Unknown Traditional Owners", "Failed")

    return render_template("acknowledgement.html", form=form)