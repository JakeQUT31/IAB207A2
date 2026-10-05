from flask_wtf import FlaskForm
from wtforms.fields import TextAreaField, SubmitField, StringField, PasswordField, BooleanField, SelectField
from wtforms.validators import InputRequired, EqualTo, Length, Regexp

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