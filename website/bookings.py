from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import db
from .models import Booking, Event

booking_bp = Blueprint('booking', __name__)

@booking_bp.route('/events/<int:id>/book', methods=['POST'])
@login_required
def book(id):
    event = db.get_or_404(Event, id)
    event.updateStatus()
    db.session.commit()

    if event.status != Event.STATUS_OPEN:
        flash(f"Sorry, this event is {event.status.lower()} and can't be booked.", "error")
        return redirect(url_for('event.show', id=id))

    ticket_type = request.form.get('ticketType')
    if ticket_type == "Player":
        spots_left = event.playerSpotsLeft()
    elif ticket_type == "Spectator":
        spots_left = event.spectatorSpotsLeft()
    else:
        flash("Please choose a ticket type.", "error")
        return redirect(url_for('event.show', id=id))

    try:
        quantity = int(request.form.get('quantity', 0))
    except ValueError:
        quantity = 0

    if spots_left == 0:
        flash(f"Sorry, there are no {ticket_type.lower()} spots left for this event.", "error")
    elif quantity < 1:
        flash("Please choose a valid quantity.", "error")
    elif quantity > spots_left:
        flash(f"Sorry, there are only {spots_left} {ticket_type.lower()} spots left for this event.", "error")
    else:
        booking = Booking(user=current_user, event=event, orderReference=ticket_type, quantity=quantity)
        db.session.add(booking)
        db.session.commit()

        event.updateStatus()  # changes to Sold Out if that was the last spot
        db.session.commit()

        flash(f"Booking confirmed! Your order ID is {booking.generateOrderID()}.", "success")
        return redirect(url_for('booking.confirmation', id=booking.bookingID))

    return redirect(url_for('event.show', id=id))

@booking_bp.route('/bookings/<int:id>')
@login_required
def confirmation(id):
    booking = db.get_or_404(Booking, id)
    if booking.userID != current_user.userID:
        abort(404)
    return render_template('booking_confirmation.html', booking=booking)

@booking_bp.route('/bookings')
@login_required
def history():
    bookings = db.session.scalars(
        db.select(Booking)
        .where(Booking.userID == current_user.userID)
        .order_by(Booking.bookingDateTime.desc())
    ).all()

    for b in bookings:
        b.event.updateStatus()
    db.session.commit()

    upcoming = [b for b in bookings if b.event.eventDate >= date.today()]
    past = [b for b in bookings if b.event.eventDate < date.today()]
    total_tickets = sum(b.quantity for b in bookings)

    return render_template('bookings.html', upcoming=upcoming, past=past,
                           order_count=len(bookings), total_tickets=total_tickets)