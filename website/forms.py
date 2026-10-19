from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from datetime import datetime
from wtforms.fields import (
  DateField,
  DecimalField,
  IntegerField,
  PasswordField,
  RadioField,
  SelectField,
  StringField,
  SubmitField,
  TextAreaField,
  TimeField,
  BooleanField,
)
from wtforms.validators import (
  DataRequired,
  EqualTo,
  InputRequired,
  Length,
  Optional,
  Regexp,
  ValidationError,
)

class EnhancedAcknowledgementForm(FlaskForm):
  enhancedMessage = TextAreaField('Custom Acknowledgement')

class CustodianForm(FlaskForm):
  custodianSearch = StringField('Search for known Custodians by entering Suburb (e.g. Corinda)')
  submit = SubmitField('Search Custodians')

class CommentForm(FlaskForm):
  text = TextAreaField('Comment', [InputRequired()])
  submit = SubmitField('Post Comment')

class LoginForm(FlaskForm):
  email = StringField('Email', [InputRequired('Enter your email address')])
  password = PasswordField('Password', [InputRequired('Enter your password')])
  remember = BooleanField('Keep me logged in')
  submit = SubmitField('Log in')

class RegisterForm(FlaskForm):
  firstName = StringField('First name', [InputRequired('Enter your first name'), Length(max=100)])
  lastName = StringField('Last name', [InputRequired('Enter your last name'), Length(max=100)])
  email = StringField('Email', [
    InputRequired('Enter your email address'),
    Regexp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', message='Enter a valid email address'),
    Length(max=120),
  ])
  phone = StringField('Mobile number', [
    InputRequired('Enter your mobile number'),
    Regexp(r'^\s*(\+?61\s?|0)4(\s?\d){8}\s*$', message='Enter a valid Australian mobile, e.g. 0412 345 678'),
  ])
  preferredContact = SelectField('Preferred contact', choices=[('Email', 'Email'), ('Phone', 'Phone'), ('SMS', 'SMS')])
  preferredLocation = SelectField('Where you usually play', choices=[
    ('Brisbane CBD', 'Brisbane CBD'),
    ('North Brisbane', 'North Brisbane'),
    ('South Brisbane', 'South Brisbane'),
    ('East Brisbane', 'East Brisbane'),
    ('West Brisbane', 'West Brisbane'),
  ])
  password = PasswordField('Password', [
    InputRequired('Choose a password'),
    Length(min=8, message='Password must be at least 8 characters'),
  ])
  confirm = PasswordField('Confirm password', [
    InputRequired('Type your password again'),
    EqualTo('password', message='Passwords do not match'),
  ])
  submit = SubmitField('Create account')

class CreateEventForm(FlaskForm):
  title = StringField('Match title', [DataRequired('Match title is required'), Length(max=150)])
  sport = SelectField('Type of sport', choices=[
    ('', 'Choose a Sport'),
    ('AFL', 'AFL'),
    ('Basketball', 'Basketball'),
    ('Cricket', 'Cricket'),
    ('Football', 'Football'),
    ('Netball', 'Netball'),
    ('Tennis', 'Tennis'),
    ('Touch Football', 'Touch Football'),
  ], validators=[InputRequired('Select a valid sport')])
  skillLevel = SelectField('Skill level', choices=[
    ('', 'Choose a Skill Level'),
    ('Amateur', 'Amateur'),
    ('Social', 'Social'),
    ('Semi-Pro', 'Semi-Pro'),
  ], validators=[InputRequired('Select a skill level')])
  surfaceType = SelectField('Surface type', choices=[
    ('', 'Choose a Surface Type'),
    ('Grass', 'Grass'),
    ('Turf', 'Turf'),
    ('Artificial Grass', 'Artificial Grass'),
    ('Indoor Court', 'Indoor Court'),
  ], validators=[InputRequired('Select a surface type')])
  tournamentName = StringField('Tournament or league name')
  description = TextAreaField('Description')
  eventDate = DateField('Date', format='%Y-%m-%d', validators=[InputRequired('Date is required')])
  startTime = TimeField('Start time', format='%H:%M', validators=[InputRequired('Start time is required')])
  endTime = TimeField('End time', format='%H:%M', validators=[InputRequired('End time is required')])
  venueName = StringField('Venue', [DataRequired('Venue is required'), Length(max=100)])
  venueAddress = StringField('Street address', [DataRequired('Street address is required'), Length(max=255)])
  venueSuburb = StringField('Suburb', [DataRequired('Suburb is required'), Length(max=100)])
  duration = IntegerField('Duration', [InputRequired('Duration is required')])
  traditionalCustodians = StringField('Traditional Custodians', [Length(max=255)])
  playerCapacity = IntegerField('Player spots', [Optional()])
  playerPrice = DecimalField('Player price', places=2, validators=[Optional()])
  spectatorCapacity = IntegerField('Spectator seats', [InputRequired('Seating capacity is required')])
  seatPrice = DecimalField('Spectator price', places=2, validators=[Optional()])
  eventImage = FileField('Event image')
  acknowledgementType = RadioField('Acknowledgement of Country', choices=[
    ('None', 'None'),
    ('Generic', 'Generic'),
    ('Enhanced', 'Enhanced'),
  ], validators=[InputRequired('Select an Acknowledgement of Country option')])

  def validate_endTime(self, field):
    if self.startTime.data and field.data and field.data <= self.startTime.data:
      raise ValidationError('End time must be after start time.')

  def validate_eventDate(self, field):
    if field.data is None or self.startTime.data is None:
      return

    event_start = datetime.combine(field.data, self.startTime.data)
    if event_start <= datetime.now():
      raise ValidationError('Event date and start time must be in the future.')

  def validate_eventImage(self, field):
    image = field.data
    if not image or not getattr(image, 'filename', ''):
      return

    extension = image.filename.rsplit('.', 1)[-1].lower() if '.' in image.filename else ''
    if extension not in {'jpg', 'jpeg', 'png', 'gif', 'webp'}:
      raise ValidationError('Upload a JPG, PNG, GIF, or WebP image.')

    image.stream.seek(0, 2)
    size = image.stream.tell()
    image.stream.seek(0)
    if size > 5 * 1024 * 1024:
      raise ValidationError('Image must be 5 MB or smaller.')

    header = image.stream.read(12)
    image.stream.seek(0)
    image_type = None
    if header.startswith(b'\xff\xd8\xff'):
      image_type = {'jpg', 'jpeg'}
    elif header.startswith(b'\x89PNG\r\n\x1a\n'):
      image_type = {'png'}
    elif header.startswith((b'GIF87a', b'GIF89a')):
      image_type = {'gif'}
    elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':
      image_type = {'webp'}
    if image_type is None or extension not in image_type:
      raise ValidationError('The selected file is not a supported image.')

  def validate_duration(self, field):
    if field.data is not None and field.data < 15:
      raise ValidationError('Duration must be at least 15 minutes.')

  def validate_playerCapacity(self, field):
    if field.data is not None and field.data < 0:
      raise ValidationError('Player capacity cannot be negative.')

  def validate_spectatorCapacity(self, field):
    if field.data is not None and field.data < 0:
      raise ValidationError('Seating capacity cannot be negative.')

  def validate_playerPrice(self, field):
    if field.data is not None and field.data < 0:
      raise ValidationError('Player price cannot be negative.')

  def validate_seatPrice(self, field):
    if field.data is not None and field.data < 0:
      raise ValidationError('Spectator price cannot be negative.')