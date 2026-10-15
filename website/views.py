from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from .models import Event, Venue
from . import db
from .forms import CustodianForm

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

    status_changed = False
    for event in events:
        old_status = event.status
        event.updateStatus()
        status_changed = status_changed or event.status != old_status
        event.playerBooked = Event.participantsBooked(event.eventID)
        event.spectatorBooked = Event.spectatorsBooked(event.eventID)
    if status_changed:
        db.session.commit()

    return render_template('index.html', events=events)


@main_bp.route('/acknowledgement', methods=['GET', 'POST'])
def acknowledgement():
    form = CustodianForm()

    if form.validate_on_submit():
        suburb = form.custodianSearch.data
        checkKnown = db.session.scalar(db.select(func.count(Venue.venueID)).select_from(Venue).where((Venue.suburb==suburb), (Venue.traditionalCustodians != "Not Specified")))

        if (checkKnown > 0):
            known = db.session.scalar(db.select(Venue.traditionalCustodians).where((Venue.suburb==suburb), (Venue.traditionalCustodians != "Not Specified")))
            flash(f"Traditional Owners: {known}!", "success")
        else:
            flash(f"Unknown Traditional Owners", "Failed")

    return render_template('acknowledgement.html', form=form)