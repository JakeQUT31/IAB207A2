from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .forms import LoginForm, RegisterForm
from .models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegisterForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        phone = _clean_phone(form.phone.data)

        # Email and phone must be unique in the database, so check before saving
        if db.session.scalar(db.select(User).where(db.func.lower(User.email) == email)):
            form.email.errors.append('An account with this email already exists. Try logging in instead.')
        if db.session.scalar(db.select(User).where(User.phone == phone)):
            form.phone.errors.append('An account with this mobile number already exists.')

        if not form.email.errors and not form.phone.errors:
            user = User(
                firstName=form.firstName.data.strip(),
                lastName=form.lastName.data.strip(),
                email=email,
                phone=phone,
                passwordhash=generate_password_hash(form.password.data),
                preferredContact=form.preferredContact.data,
                preferredLocation=form.preferredLocation.data,
            )
            db.session.add(user)
            db.session.commit()

            # Log them straight in so they don't have to type it all again
            login_user(user)
            flash(f"Welcome to SportTix, {user.firstName}!", "success")
            return redirect(url_for('main.index'))

    return render_template('register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    error = None

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = db.session.scalar(db.select(User).where(db.func.lower(User.email) == email))

        if user is None or not _password_matches(user.passwordhash, form.password.data):
            error = 'Invalid email or password'
        else:
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.firstName}!", "success")

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/') and not next_page.startswith('//'):
                return redirect(next_page)
            return redirect(url_for('main.index'))

    return render_template('login.html', form=form, error=error)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('main.index'))


def _password_matches(stored_hash, password):
    try:
        return check_password_hash(stored_hash, password)
    except (ValueError, TypeError):
        return False


def _clean_phone(phone):
    # Store every number the same way (e.g. "0412345678") so duplicates are caught
    digits = ''.join(ch for ch in phone if ch.isdigit())
    if digits.startswith('61'):
        digits = '0' + digits[2:]
    return digits