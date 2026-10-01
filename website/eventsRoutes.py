from flask import Blueprint, render_template, request, redirect, url_for
from .models import Event, Comment, Venue, User, Category, Booking
from . import db
from .forms import CommentForm
from sqlalchemy import func

event_bp = Blueprint('event', __name__, url_prefix='/events')

@event_bp.route('/<id>')
def show(id):
   print("The id is: " + str(id))
   event = db.session.scalar(db.select(Event).where(Event.eventID==id))
   print("The event.eventID is: " + str(event.eventID))
   venue = db.session.scalar(db.select(Venue).where(Venue.venueID==event.venueID))
   user = db.session.scalar(db.select(User).where(User.userID==event.creatorID))
   category = db.session.scalar(db.select(Category).where(Category.categoryID==event.categoryID))
   comment = db.session.scalar(db.select(Comment).where(Comment.eventID==id))
   spectatorBooked = Event.spectatorsBooked(id)
   playerBooked = Event.participantsBooked(id)
   spectatorAvailable = event.spectatorCapacity - spectatorBooked
   playerAvailable = event.participantCapacity - playerBooked
   cform = CommentForm()  
   return render_template('events/event.html', event=event, venue=venue, user=user, category=category, comment=comment, spectatorBooked=spectatorBooked, playerBooked=playerBooked, spectatorAvailable=spectatorAvailable, playerAvailable=playerAvailable, form=cform)


@event_bp.route('/<id>/comment', methods=['GET', 'POST'])  
def comment(id):  
   print("Comment route ID: " + str(id))
   form = CommentForm()
   event = db.session.scalar(db.select(Event).where(Event.eventID==id))
   user = db.session.scalar(db.select(User).where(User.userID==1))
   if form.validate_on_submit():
     comment = Comment(content=form.text.data, user=user, event=event)
     db.session.add(comment) 
     db.session.commit()
     print('Your comment has been added', 'success')
   else:
      print('Your comment failed', 'error')
   
   # using redirect sends a GET request to destination.show
   print("Redirect ID: " + str(id))
   return redirect(url_for('event.show', id=id))