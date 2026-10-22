from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import pytest

from website import create_app, db
from website.models import Booking, Event, User


@pytest.fixture
def app(tmp_path):
    app = create_app({
        'TESTING': True,
        'PROPAGATE_EXCEPTIONS': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })
    app.static_folder = str(tmp_path / 'static')
    with app.app_context():
        db.create_all()
        owner = User(
            firstName='Event', lastName='Owner', email='owner@example.com',
            phone='0412345678', passwordhash='test', preferredContact='Email',
            preferredLocation='Brisbane CBD',
        )
        other = User(
            firstName='Other', lastName='User', email='other@example.com',
            phone='0412345679', passwordhash='test', preferredContact='Email',
            preferredLocation='Brisbane CBD',
        )
        db.session.add_all([owner, other])
        db.session.commit()
        app.test_owner_id = owner.userID
        app.test_other_id = other.userID
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture

def client(app):
    return app.test_client()


def login(client, user_id):
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True


def event_data(**overrides):
    data = {
        'title': 'Community Football',
        'sport': 'Football',
        'skillLevel': 'Social',
        'surfaceType': 'Grass',
        'tournamentName': '',
        'description': 'A community game',
        'eventDate': (date.today() + timedelta(days=3)).isoformat(),
        'startTime': '18:00',
        'endTime': '19:00',
        'venueName': 'Local Oval',
        'venueAddress': '1 Main Road',
        'venueSuburb': 'Brisbane',
        'duration': '60',
        'traditionalCustodians': '',
        'playerCapacity': '1',
        'playerPrice': '10.00',
        'spectatorCapacity': '1',
        'seatPrice': '5.00',
        'acknowledgementType': 'Generic',
    }
    data.update(overrides)
    return data


def create_event(client, app, **overrides):
    login(client, app.test_owner_id)
    response = client.post('/events/create', data=event_data(**overrides))
    assert response.status_code == 302
    return int(response.location.rsplit('/', 1)[-1])


def test_event_edit_is_limited_to_creator(client, app):
    event_id = create_event(client, app)

    login(client, app.test_other_id)
    assert client.get(f'/events/{event_id}/edit').status_code == 403
    assert client.post(f'/events/{event_id}/cancel').status_code == 403

    login(client, app.test_owner_id)
    response = client.post(
        f'/events/{event_id}/edit',
        data=event_data(title='Updated Community Game'),
    )
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Event, event_id).title == 'Updated Community Game'


def test_edit_form_renders_on_get_and_validation_errors(client, app):
    event_id = create_event(client, app)
    login(client, app.test_owner_id)

    edit_page = client.get(f'/events/{event_id}/edit')
    assert edit_page.status_code == 200
    assert b'Browse events card' in edit_page.data
    assert b'name="enhancedMessage"' in edit_page.data

    invalid_update = client.post(
        f'/events/{event_id}/edit',
        data=event_data(title=''),
    )
    assert invalid_update.status_code == 200
    assert b'Match title is required' in invalid_update.data


def test_past_event_start_is_rejected_for_create_and_edit(client, app):
    login(client, app.test_owner_id)
    past_date_response = client.post(
        '/events/create',
        data=event_data(eventDate=(date.today() - timedelta(days=1)).isoformat()),
    )
    assert past_date_response.status_code == 200
    assert b'Event date and start time must be in the future.' in past_date_response.data

    past_time_response = client.post(
        '/events/create',
        data=event_data(eventDate=date.today().isoformat(), startTime='00:00', endTime='01:00'),
    )
    assert past_time_response.status_code == 200
    assert b'Event date and start time must be in the future.' in past_time_response.data

    event_id = create_event(client, app)
    past_edit_response = client.post(
        f'/events/{event_id}/edit',
        data=event_data(eventDate=(date.today() - timedelta(days=1)).isoformat()),
    )
    assert past_edit_response.status_code == 200
    assert b'Event date and start time must be in the future.' in past_edit_response.data


def test_event_can_be_cancelled_and_cannot_be_edited_afterward(client, app):
    event_id = create_event(client, app)
    login(client, app.test_owner_id)

    response = client.post(f'/events/{event_id}/cancel')
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Event, event_id).status == Event.STATUS_CANCELLED

    response = client.get(f'/events/{event_id}/edit')
    assert response.status_code == 302


def test_event_status_updates_from_bookings_and_date(client, app):
    event_id = create_event(client, app)
    with app.app_context():
        event = db.session.get(Event, event_id)
        db.session.add_all([
            Booking(userID=app.test_owner_id, eventID=event_id, orderReference='Player'),
            Booking(userID=app.test_other_id, eventID=event_id, orderReference='Spectator'),
        ])
        db.session.commit()

    assert client.get(f'/events/{event_id}').status_code == 200
    with app.app_context():
        event = db.session.get(Event, event_id)
        assert event.status == Event.STATUS_SOLD_OUT
        event.eventDate = date.today() - timedelta(days=1)
        event.status = Event.STATUS_OPEN
        db.session.commit()

    assert client.get('/').status_code == 200
    with app.app_context():
        assert db.session.get(Event, event_id).status == Event.STATUS_INACTIVE


def test_event_image_upload_and_invalid_image(client, app, tmp_path):
    login(client, app.test_owner_id)
    valid_image = BytesIO(b'\x89PNG\r\n\x1a\n' + b'IHDR' + b'\x00' * 8)
    response = client.post(
        '/events/create',
        data=event_data(eventImage=(valid_image, 'field.png', 'image/png')),
        content_type='multipart/form-data',
    )
    assert response.status_code == 302
    with app.app_context():
        event = db.session.scalar(db.select(Event).where(Event.title == 'Community Football'))
        assert event.imageURL.startswith('/static/uploads/')
        assert Path(app.static_folder, event.imageURL.removeprefix('/static/')).is_file()

    invalid_image = BytesIO(b'not an image')
    response = client.post(
        '/events/create',
        data=event_data(title='Rejected Image', eventImage=(invalid_image, 'fake.png', 'image/png')),
        content_type='multipart/form-data',
    )
    assert response.status_code == 200
    assert b'The selected file is not a supported image.' in response.data


def test_custom_not_found_and_internal_error_pages(client, app):
    def raise_error():
        raise RuntimeError('intentional test error')

    app.add_url_rule('/__test_500', 'test_500', raise_error)
    not_found = client.get('/not-a-real-page')
    internal_error = client.get('/__test_500')

    assert not_found.status_code == 404
    assert b'We couldn' in not_found.data
    assert internal_error.status_code == 500
    assert b'Something went wrong' in internal_error.data
