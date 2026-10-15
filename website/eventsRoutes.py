import os
from decimal import Decimal
from uuid import uuid4

from flask import Blueprint, abort, current_app, flash, render_template, request, redirect, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from .models import Event, Comment, Venue, User, Category
from . import db
from .forms import CommentForm, CreateEventForm, EnhancedAcknowledgementForm
from sqlalchemy import func
from sqlalchemy.orm import joinedload

event_bp = Blueprint('event', __name__, url_prefix='/events')

SPORTS = ('AFL', 'Basketball', 'Cricket', 'Football', 'Netball', 'Tennis', 'Touch Football')
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}


def _store_event_image(upload):
   extension = secure_filename(upload.filename).rsplit('.', 1)[-1].lower()
   if extension not in ALLOWED_IMAGE_EXTENSIONS:
      raise ValueError('Unsupported image extension after form validation.')
   filename = f'{uuid4().hex}.{extension}'
   upload_directory = os.path.join(current_app.static_folder, 'uploads')
   os.makedirs(upload_directory, exist_ok=True)
   upload.save(os.path.join(upload_directory, filename))
   return url_for('static', filename=f'uploads/{filename}')


def _remove_event_image(image_url):
   if not image_url or not image_url.startswith('/static/uploads/'):
      return
   filename = os.path.basename(image_url)
   if filename:
      image_path = os.path.join(current_app.static_folder, 'uploads', filename)
      if os.path.isfile(image_path):
         os.remove(image_path)


def _event_form_data(event):
   return {
      'title': event.title,
      'sport': event.category.categoryName,
      'skillLevel': event.skillLevel,
      'surfaceType': event.surfaceType,
      'tournamentName': event.format or '',
      'description': event.description or '',
      'eventDate': event.eventDate.isoformat(),
      'startTime': event.startTime.strftime('%H:%M'),
      'endTime': event.endTime.strftime('%H:%M'),
      'venueName': event.venue.venueName,
      'venueAddress': event.venue.address,
      'venueSuburb': event.venue.suburb,
      'duration': event.duration,
      'traditionalCustodians': event.venue.traditionalCustodians or '',
      'playerCapacity': event.participantCapacity,
      'playerPrice': event.participantPrice,
      'spectatorCapacity': event.spectatorCapacity,
      'seatPrice': event.spectatorPrice,
      'acknowledgementType': event.acknowledgementType,
   }


def _refresh_event_statuses(events):
   changed = False
   for event in events:
      previous_status = event.status
      event.updateStatus()
      changed = changed or event.status != previous_status
   if changed:
      db.session.commit()


@event_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
   form = CreateEventForm()
   aform = EnhancedAcknowledgementForm()
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

      checkKnown = db.session.scalar(db.select(func.count(Venue.venueID)).select_from(Venue).where((Venue.suburb==form.venueSuburb.data.strip()), (Venue.address==form.venueAddress.data.strip()), (Venue.traditionalCustodians != "Not Specified")))

      if (checkKnown != 0):
         print("Check: " + str(checkKnown))
         known = db.session.scalar(db.select(Venue.traditionalCustodians).where((Venue.suburb==form.venueSuburb.data.strip()), (Venue.address==form.venueAddress.data.strip()), (Venue.traditionalCustodians != "Not Specified")))
         print("Found: " + known)
      else:
         print("Here")
         known = (form.traditionalCustodians.data or '').strip() or 'Not Specified'
         print("here2")

      respects = (form.acknowledgementType.data or '').strip() or 'None'

      if (respects == "Enhanced"):
         respects = aform.enhancedMessage.data
      elif (respects == "Generic"):
         respects = "I would like to begin by acknowledging the Traditional Owners of the land on which we meet today. I would also like to pay my respects to Elders past and present."
      else:
         respects = ''
      
      print("Going In: " + known)

      venue = Venue(
         venueName=form.venueName.data.strip(),
         address=form.venueAddress.data.strip(),
         suburb=form.venueSuburb.data.strip(),
         capacity=max(spectator_capacity + player_capacity, 1),
         traditionalCustodians=known,
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
         acknowledgementType=respects,
      )
      if form.eventImage.data:
         event.imageURL = _store_event_image(form.eventImage.data)
      db.session.add(event)
      db.session.commit()
      flash(f'Event "{event.title}" has been published.', 'success')
      return redirect(url_for('event.show', id=event.eventID))

   errors = [message for field_errors in form.errors.values() for message in field_errors]
   return render_template('create_event.html', sports=SPORTS, errors=errors, form_data=request.form, form=form, aform=aform, aform_data=request.form, is_edit=False)


@event_bp.route('/mine')
@login_required
def my_events():
   events = db.session.scalars(
      db.select(Event)
      .where(Event.creatorID == current_user.userID)
      .options(joinedload(Event.category), joinedload(Event.venue))
      .order_by(Event.eventDate, Event.startTime)
   ).all()
   _refresh_event_statuses(events)
   return render_template('events/my_events.html', events=events)


@event_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
   event = db.session.get(Event, id)
   if event is None:
      abort(404)
   if not event.canBeEditedBy(current_user):
      abort(403)
   if event.status == Event.STATUS_CANCELLED:
      flash('Cancelled events cannot be edited.', 'warning')
      return redirect(url_for('event.my_events'))

   form = CreateEventForm()
   if request.method == 'GET':
      form.title.data = event.title
      form.sport.data = event.category.categoryName
      form.skillLevel.data = event.skillLevel
      form.surfaceType.data = event.surfaceType
      form.tournamentName.data = event.format or ''
      form.description.data = event.description or ''
      form.eventDate.data = event.eventDate
      form.startTime.data = event.startTime
      form.endTime.data = event.endTime
      form.venueName.data = event.venue.venueName
      form.venueAddress.data = event.venue.address
      form.venueSuburb.data = event.venue.suburb
      form.duration.data = event.duration
      form.traditionalCustodians.data = event.venue.traditionalCustodians or ''
      form.playerCapacity.data = event.participantCapacity
      form.playerPrice.data = event.participantPrice
      form.spectatorCapacity.data = event.spectatorCapacity
      form.seatPrice.data = event.spectatorPrice
      form.acknowledgementType.data = event.acknowledgementType

   if form.validate_on_submit():
      category = db.session.scalar(
         db.select(Category).where(func.lower(Category.categoryName) == form.sport.data.lower())
      )
      if category is None:
         category = Category(categoryName=form.sport.data, description=f'{form.sport.data} events')
         db.session.add(category)

      event.category = category
      event.title = form.title.data.strip()
      event.description = (form.description.data or '').strip() or None
      event.eventDate = form.eventDate.data
      event.startTime = form.startTime.data
      event.endTime = form.endTime.data
      event.duration = form.duration.data
      event.surfaceType = form.surfaceType.data
      event.skillLevel = form.skillLevel.data
      event.format = (form.tournamentName.data or '').strip() or None
      event.participantCapacity = form.playerCapacity.data or 0
      event.spectatorCapacity = form.spectatorCapacity.data
      event.participantPrice = form.playerPrice.data or Decimal('0')
      event.spectatorPrice = form.seatPrice.data or Decimal('0')
      event.acknowledgementType = form.acknowledgementType.data
      event.venue.venueName = form.venueName.data.strip()
      event.venue.address = form.venueAddress.data.strip()
      event.venue.suburb = form.venueSuburb.data.strip()
      event.venue.capacity = max(event.participantCapacity + event.spectatorCapacity, 1)
      event.venue.traditionalCustodians = (form.traditionalCustodians.data or '').strip() or 'Not specified'
      if form.eventImage.data:
         old_image = event.imageURL
         event.imageURL = _store_event_image(form.eventImage.data)
         _remove_event_image(old_image)
      event.updateStatus()
      db.session.commit()
      flash(f'Event "{event.title}" has been updated.', 'success')
      return redirect(url_for('event.show', id=event.eventID))

   errors = [message for field_errors in form.errors.values() for message in field_errors]
   form_data = request.form if request.method == 'POST' else _event_form_data(event)
   return render_template('create_event.html', sports=SPORTS, errors=errors, form_data=form_data, form=form, is_edit=True, event=event)


@event_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
def cancel(id):
   event = db.session.get(Event, id)
   if event is None:
      abort(404)
   if not event.canBeEditedBy(current_user):
      abort(403)
   if event.status != Event.STATUS_CANCELLED:
      event.cancel()
      db.session.commit()
      flash(f'Event "{event.title}" has been cancelled.', 'success')
   else:
      flash('This event is already cancelled.', 'warning')
   return redirect(url_for('event.my_events'))


@event_bp.route('/<int:id>')
def show(id):
   event = db.session.scalar(db.select(Event).where(Event.eventID==id))
   if event is None:
      abort(404)
   previous_status = event.status
   event.updateStatus()
   if event.status != previous_status:
      db.session.commit()
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