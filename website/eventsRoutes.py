from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, render_template, request, redirect, url_for
from flask_login import current_user, login_required
from .models import Event, Comment, Venue, User, Category
from . import db
from .forms import CommentForm
from sqlalchemy import func
from sqlalchemy.orm import joinedload

event_bp = Blueprint('event', __name__, url_prefix='/events')

SPORTS = ('AFL', 'Basketball', 'Cricket', 'Football', 'Netball', 'Tennis', 'Touch Football')


@event_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
   errors = []
   if request.method == 'POST':
      required_fields = {
         'title': 'Match title',
         'sport': 'Type of sport',
         'eventDate': 'Date',
         'startTime': 'Start time',
         'endTime': 'End time',
         'venueName': 'Venue',
         'venueAddress': 'Street address',
         'venueSuburb': 'Suburb',
         'duration': 'Duration',
         'spectatorCapacity': 'Seating capacity',
         'surfaceType': 'Surface type',
         'skillLevel': 'Skill level',
      }
      for field, label in required_fields.items():
         if not request.form.get(field, '').strip():
            errors.append(f'{label} is required.')

      sport = request.form.get('sport', '').strip()
      surface = request.form.get('surfaceType', '').strip()
      skill = request.form.get('skillLevel', '').strip()
      acknowledgement = request.form.get('acknowledgementType', Event.ACK_NONE)
      if sport not in SPORTS:
         errors.append('Select a valid sport.')
      if surface not in (Event.SURFACE_TURF, Event.SURFACE_INDOOR_COURT,
                         Event.SURFACE_ARTIFICIAL_GRASS, Event.SURFACE_GRASS):
         errors.append('Select a valid surface type.')
      if skill not in (Event.SKILL_AMATEUR, Event.SKILL_SOCIAL, Event.SKILL_SEMI_PRO):
         errors.append('Select a valid skill level.')
      if acknowledgement not in (Event.ACK_NONE, Event.ACK_GENERIC, Event.ACK_ENHANCED):
         errors.append('Select a valid Acknowledgement of Country option.')

      try:
         event_date = datetime.strptime(request.form.get('eventDate', ''), '%Y-%m-%d').date()
         start_time = datetime.strptime(request.form.get('startTime', ''), '%H:%M').time()
         end_time = datetime.strptime(request.form.get('endTime', ''), '%H:%M').time()
         if end_time <= start_time:
            errors.append('End time must be after start time.')
      except ValueError:
         event_date = start_time = end_time = None
         if not any('required.' in error for error in errors):
            errors.append('Enter a valid date and start/end time.')

      integer_values = {}
      for field, label, required, minimum in (
         ('duration', 'Duration', True, 15),
         ('spectatorCapacity', 'Seating capacity', True, 0),
         ('playerCapacity', 'Player capacity', False, 0),
      ):
         raw_value = request.form.get(field, '').strip()
         if not raw_value and not required:
            integer_values[field] = 0
            continue
         try:
            integer_values[field] = int(raw_value)
            if integer_values[field] < minimum:
               errors.append(f'{label} must be at least {minimum}.')
         except ValueError:
            if raw_value:
               errors.append(f'{label} must be a whole number.')

      price_values = {}
      for field, label in (('playerPrice', 'Player price'), ('seatPrice', 'Spectator price')):
         raw_value = request.form.get(field, '').strip()
         try:
            price_values[field] = Decimal(raw_value or '0')
            if price_values[field] < 0:
               errors.append(f'{label} cannot be negative.')
         except InvalidOperation:
            errors.append(f'{label} must be a valid amount.')

      if not errors:
         category = db.session.scalar(
            db.select(Category).where(func.lower(Category.categoryName) == sport.lower())
         )
         if category is None:
            category = Category(categoryName=sport, description=f'{sport} events')
            db.session.add(category)

         spectator_capacity = integer_values['spectatorCapacity']
         player_capacity = integer_values['playerCapacity']
         venue = Venue(
            venueName=request.form['venueName'].strip(),
            address=request.form['venueAddress'].strip(),
            suburb=request.form['venueSuburb'].strip(),
            capacity=max(spectator_capacity + player_capacity, 1),
            traditionalCustodians=request.form.get('traditionalCustodians', '').strip() or 'Not specified',
         )
         event = Event(
            creator=current_user,
            category=category,
            venue=venue,
            title=request.form['title'].strip(),
            description=request.form.get('description', '').strip() or None,
            eventDate=event_date,
            startTime=start_time,
            endTime=end_time,
            duration=integer_values['duration'],
            surfaceType=surface,
            skillLevel=skill,
            format=request.form.get('tournamentName', '').strip() or None,
            participantCapacity=player_capacity,
            spectatorCapacity=spectator_capacity,
            participantPrice=price_values['playerPrice'],
            spectatorPrice=price_values['seatPrice'],
            status=Event.STATUS_OPEN,
            acknowledgementType=acknowledgement,
         )
         db.session.add(event)
         db.session.commit()
         return redirect(url_for('event.show', id=event.eventID))

   return render_template('create_event.html', sports=SPORTS, errors=errors, form_data=request.form)


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

# Generates a page with detailed information regading a specific event
@event_bp.route('/<int:id>')
def show(id):
   # This code collects the various details about the event from the sql database
   event = db.session.scalar(db.select(Event).where(Event.eventID==id))
   if event is None:
      abort(404)
   category = db.session.scalar(db.select(Category).where(Category.categoryID==event.categoryID))
   venue = db.session.scalar(db.select(Venue).where(Venue.venueID==event.venueID))
   user = db.session.scalar(db.select(User).where(User.userID==event.creatorID))
   commentCount = db.session.scalar(db.select(func.count(Comment.commentID)).select_from(Comment).where((Comment.eventID==id)))
   spectatorBooked = Event.spectatorsBooked(id)
   playerBooked = Event.participantsBooked(id)
   spectatorAvailable = event.spectatorCapacity - spectatorBooked
   playerAvailable = event.participantCapacity - playerBooked

   if current_user.is_authenticated:
      loggedUser = db.session.scalar(db.select(User).where(User.userID==current_user.userID))
   else:
      loggedUser = db.session.scalar(db.select(User).where(User.userID==1))

   cform = CommentForm()  
   return render_template('events/event.html', event=event, venue=venue, user=user, category=category, comment=comment, commentCount=commentCount, spectatorBooked=spectatorBooked, playerBooked=playerBooked, spectatorAvailable=spectatorAvailable, playerAvailable=playerAvailable, loggedUser=loggedUser, form=cform)


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