from decimal import Decimal

from flask import Blueprint, abort, flash, render_template, request, redirect, url_for
from flask_login import current_user, login_required
from .models import Event, Comment, Venue, User, Category
from . import db
from .forms import CommentForm, CreateEventForm
from sqlalchemy import func
from sqlalchemy.orm import joinedload

event_bp = Blueprint('event', __name__, url_prefix='/events')

SPORTS = ('AFL', 'Basketball', 'Cricket', 'Football', 'Netball', 'Tennis', 'Touch Football')


@event_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
   form = CreateEventForm()
   if form.validate_on_submit():
      sport = form.sport.data
      category = db.session.scalar(
         db.select(Category).where(func.lower(Category.categoryName) == sport.lower())
      )
      if category is None:
         category = Category(categoryName=sport, description=f'{sport} events')
         db.session.add(category)

      player_capacity = form.playerCapacity.data or 0
      spectator_capacity = form.spectatorCapacity.data
      venue = Venue(
         venueName=form.venueName.data.strip(),
         address=form.venueAddress.data.strip(),
         suburb=form.venueSuburb.data.strip(),
         capacity=max(spectator_capacity + player_capacity, 1),
         traditionalCustodians=(form.traditionalCustodians.data or '').strip() or 'Not specified',
      )
      event = Event(
         creator=current_user,
         category=category,
         venue=venue,
         title=form.title.data.strip(),
         description=(form.description.data or '').strip() or None,
         eventDate=form.eventDate.data,
         startTime=form.startTime.data,
         endTime=form.endTime.data,
         duration=form.duration.data,
         surfaceType=form.surfaceType.data,
         skillLevel=form.skillLevel.data,
         format=(form.tournamentName.data or '').strip() or None,
         participantCapacity=player_capacity,
         spectatorCapacity=spectator_capacity,
         participantPrice=form.playerPrice.data or Decimal('0'),
         spectatorPrice=form.seatPrice.data or Decimal('0'),
         status=Event.STATUS_OPEN,
         acknowledgementType=form.acknowledgementType.data,
      )
      db.session.add(event)
      db.session.commit()
      flash(f'Event "{event.title}" has been published.', 'success')
      return redirect(url_for('event.show', id=event.eventID))

   errors = [message for field_errors in form.errors.values() for message in field_errors]
   return render_template('create_event.html', sports=SPORTS, errors=errors, form_data=request.form, form=form)


@event_bp.route('/mine')
@login_required
def my_events():
   events = db.session.scalars(
      db.select(Event)
      .where(Event.creatorID == current_user.userID)
      .options(joinedload(Event.category), joinedload(Event.venue))
      .order_by(Event.eventDate, Event.startTime)
   ).all()
   return render_template('events/my_events.html', events=events)


@event_bp.route('/<int:id>')
def show(id):
   event = db.session.scalar(db.select(Event).where(Event.eventID==id))
   if event is None:
      abort(404)
   category = db.session.scalar(db.select(Category).where(Category.categoryID==event.categoryID))
   venue = db.session.scalar(db.select(Venue).where(Venue.venueID==event.venueID))
   user = db.session.scalar(db.select(User).where(User.userID==event.creatorID))
   comment = db.session.scalar(db.select(Comment).where(Comment.eventID==id))
   spectatorBooked = Event.spectatorsBooked(id)
   playerBooked = Event.participantsBooked(id)
   spectatorAvailable = event.spectatorCapacity - spectatorBooked
   playerAvailable = event.participantCapacity - playerBooked

   if current_user.is_authenticated:
      loggedUser = db.session.scalar(db.select(User).where(User.userID==current_user.userID))
   else:
      loggedUser = db.session.scalar(db.select(User).where(User.userID==1))

   cform = CommentForm()  
   return render_template('events/event.html', event=event, venue=venue, user=user, category=category, comment=comment, spectatorBooked=spectatorBooked, playerBooked=playerBooked, spectatorAvailable=spectatorAvailable, playerAvailable=playerAvailable, loggedUser=loggedUser, form=cform)


@event_bp.route('/<int:id>/comment', methods=['GET', 'POST'])
def comment(id):  
   form = CommentForm()
   event = db.session.scalar(db.select(Event).where(Event.eventID==id))
   if event is None:
      abort(404)
   user = db.session.scalar(db.select(User).where(User.userID==current_user.userID))
   if form.validate_on_submit():
      print("Test 1: " + str(current_user))
      print("Test 2: " + str(current_user.userID))
      comment = Comment(content=form.text.data, user=current_user, event=event)
      db.session.add(comment) 
      db.session.commit()
      print('Your comment has been added', 'success')
   else:
      print('Your comment failed', 'error')
   
   # using redirect sends a GET request to destination.show
   return redirect(url_for('event.show', id=id))