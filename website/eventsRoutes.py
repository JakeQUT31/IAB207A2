from flask import Blueprint, render_template, request, redirect, url_for
from .models import Event, Comment, Venue, User, Category
from . import db

event_bp = Blueprint('event', __name__, url_prefix='/events')

@event_bp.route('/<id>')
def show(id):
   event = db.session.scalar(db.select(Event).where(Event.eventID==id))
   venue = db.session.scalar(db.select(Venue).where(Venue.venueID==event.venueID))
   user = db.session.scalar(db.select(User).where(User.userID==event.creatorID))
   category = db.session.scalar(db.select(Category).where(Category.categoryID==event.categoryID))
   return render_template('events/event.html', event=event, venue=venue, user=user, category=category)