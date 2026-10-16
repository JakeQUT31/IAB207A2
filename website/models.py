from datetime import datetime, date
from flask_login import UserMixin
from sqlalchemy.orm import validates
from sqlalchemy import func
from . import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    userID = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String(100), nullable=False)
    lastName = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    passwordhash = db.Column(db.String(255), nullable=False)
    preferredContact = db.Column(db.String(20), nullable=False)
    preferredLocation = db.Column(db.String(100), nullable=False)

    events = db.relationship("Event", back_populates = "creator", cascade = "all, delete-orphan")
    bookings = db.relationship("Booking", back_populates = "user", cascade = "all, delete-orphan")
    comments = db.relationship("Comment", back_populates = "user", cascade = "all, delete-orphan")

    def get_id(self):
        return str(self.userID)
    def viewBookingHistory(self):
        return self.bookings

    def __repr__(self):
        return f"<User({self.userID}, {self.email})>"

class Category(db.Model):
    __tablename__ = 'categories'

    categoryID = db.Column(db.Integer, primary_key=True)
    categoryName = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)

    events = db.relationship("Event", back_populates = "category")
    def getEvents(self):
        return self.events
    
    def __repr__(self):
        return f"<Category{self.categoryID}, {self.categoryName}>"


class Venue(db.Model):
    __tablename__= 'venues'

    venueID = db.Column(db.Integer, primary_key=True)
    venueName = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    suburb = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    traditionalCustodians = db.Column(db.String(255), nullable=False)
    parking = db.Column(db.Text, nullable=True)

    events = db.relationship("Event", back_populates = "venue")
    def getTraditionalCustodians(self):
        return self.traditionalCustodians

    def __repr__(self):
        return f"<Venue{self.venueID}, {self.venueName}, {self.suburb}>"

class Event(db.Model):
    __tablename__ = "events"
 
    STATUS_OPEN = "Open"
    STATUS_INACTIVE = "Inactive"
    STATUS_SOLD_OUT = "Sold Out"
    STATUS_CANCELLED = "Cancelled"
 
    SKILL_AMATEUR = "Amateur"
    SKILL_SOCIAL = "Social"
    SKILL_SEMI_PRO = "Semi-Pro"
 
    SURFACE_TURF = "Turf"
    SURFACE_INDOOR_COURT = "Indoor Court"
    SURFACE_ARTIFICIAL_GRASS = "Artificial Grass"
    SURFACE_GRASS = "Grass"
 
    ACK_NONE = "None"
    ACK_GENERIC = "Generic"
    ACK_ENHANCED = "Enhanced"
 
    eventID = db.Column(db.Integer, primary_key=True)
    creatorID = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)
    categoryID = db.Column(db.Integer, db.ForeignKey("categories.categoryID"), nullable=False)
    venueID = db.Column(db.Integer, db.ForeignKey("venues.venueID"), nullable=False)
 
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    bring = db.Column(db.Text, nullable=True)
    imageURL = db.Column(db.String(150), nullable=True)
 
    eventDate = db.Column(db.Date, nullable=False)
    startTime = db.Column(db.Time, nullable=False)
    endTime = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
 
    surfaceType = db.Column(db.String(30), nullable=False)
    skillLevel = db.Column(db.String(20), nullable=False)
    format = db.Column(db.Text, nullable=True)
 
    participantCapacity = db.Column(db.Integer, nullable=False, default=0)
    spectatorCapacity = db.Column(db.Integer, nullable=False, default=0)
    participantPrice = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    spectatorPrice = db.Column(db.Numeric(8, 2), nullable=False, default=0)
 
    status = db.Column(db.String(20), nullable=False, default=STATUS_OPEN)
    acknowledgementType = db.Column(db.String(150), nullable=False, default=ACK_NONE)
 
    creator = db.relationship("User", back_populates="events")
    category = db.relationship("Category", back_populates="events")
    venue = db.relationship("Venue", back_populates="events")
    bookings = db.relationship("Booking", back_populates="event", cascade="all, delete-orphan")
    comments = db.relationship("Comment", back_populates="event", cascade="all, delete-orphan")
 
    # def getBookedCount(self, ticket_type):
    #     total = 0
    #     for booking in self.bookings:
    #         for ticket in booking.tickets:
    #             if ticket.ticketType == ticket_type:
    #                 total += 1
    #     return total

    @staticmethod
    def participantsBooked(id):
        return db.session.scalar(
            db.select(func.coalesce(func.sum(Booking.quantity), 0))
            .where((Booking.eventID == id) & (Booking.orderReference == "Player"))
        )

    @staticmethod
    def spectatorsBooked(id):
        return db.session.scalar(
            db.select(func.coalesce(func.sum(Booking.quantity),0))
            .where((Booking.eventID == id) & (Booking.orderReference == "Spectator"))) 

    def playerSpotsLeft(self):
        return max(self.participantCapacity - Event.participantsBooked(self.eventID), 0)

    def spectatorSpotsLeft(self):
        return max(self.spectatorCapacity - Event.spectatorsBooked(self.eventID), 0)

    def isSoldOut(self):
        return self.playerSpotsLeft() == 0 and self.spectatorSpotsLeft() == 0
    
    def updateStatus(self):
        if self.status == self.STATUS_CANCELLED:
            return self.status
        if self.eventDate < date.today():
            self.status = self.STATUS_INACTIVE
        elif self.isSoldOut():
            self.status = self.STATUS_SOLD_OUT
        else:
            self.status = self.STATUS_OPEN
        return self.status
 
    def cancel(self):
        self.status = self.STATUS_CANCELLED
 
    def canBeEditedBy(self, user):
        return user is not None and user.userID == self.creatorID
 
    def __repr__(self):
        return f"<Event {self.eventID} {self.title!r} ({self.status})>"
 
 
class Booking(db.Model):
    __tablename__ = "bookings"
 
    bookingID = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)
    eventID = db.Column(db.Integer, db.ForeignKey("events.eventID"), nullable=False)
 
    orderReference = db.Column(db.String(150), nullable=True)
    bookingDateTime = db.Column(db.DateTime, default=datetime.now)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    user = db.relationship("User", back_populates="bookings")
    event = db.relationship("Event", back_populates="bookings")
 
    def generateOrderID(self):
        return f"SPTX-{self.bookingID:06d}"

    def ticketPrice(self):
        if self.orderReference == "Player":
            return self.event.participantPrice
        return self.event.spectatorPrice
    def totalPrice(self):
        return self.ticketPrice() * self.quantity
    # --------Commenting out legacy code in case it needs to be used (will need to be modified to work)--------
    # def calculateTotal(self):
    #     return sum(ticket.price for ticket in self.tickets)
 
    # def confirm(self):
    #     # This will need updating to work as orderReference has changed purpose
    #     self.generateOrderID()
    #     self.event.updateStatus()
    #     return self.orderReference
 
    def __repr__(self):
        return f"<Booking {self.bookingID} user={self.userID} event={self.eventID}>"
 
 
# class Ticket(db.Model):
#     __tablename__ = "tickets"
 
#     TYPE_PARTICIPANT = "Participant"
#     TYPE_SPECTATOR = "Spectator"
 
#     ticketID = db.Column(db.Integer, primary_key=True)
#     bookingID = db.Column(db.Integer, db.ForeignKey("bookings.bookingID"), nullable=False)
 
#     ticketType = db.Column(db.String(150), nullable=False)
#     price = db.Column(db.Numeric(8, 2), nullable=False)
 
#     booking = db.relationship("Booking", back_populates="tickets")
 
#     @validates("ticketType")
#     def validate_ticket_type(self, key, value):
#         if value not in (self.TYPE_PARTICIPANT, self.TYPE_SPECTATOR):
#             raise ValueError(f"Invalid ticketType: {value}")
#         return value
 
#     def getPrice(self):
#         return self.price
 
#     def __repr__(self):
#         return f"<Ticket {self.ticketID} {self.ticketType} ${self.price}>"
 
 
class Comment(db.Model):
    __tablename__ = "comments"
 
    commentID = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)
    eventID = db.Column(db.Integer, db.ForeignKey("events.eventID"), nullable=False)
 
    content = db.Column(db.Text, nullable=False)
    postedDateTime = db.Column(db.DateTime, default=datetime.now)
 
    user = db.relationship("User", back_populates="comments")
    event = db.relationship("Event", back_populates="comments")
 
    def getAuthorName(self):
        return f"{self.user.firstName} {self.user.lastName}"
 
    def __repr__(self):
        return f"<Comment {self.commentID} on event={self.eventID}>"
 