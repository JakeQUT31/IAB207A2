from flask import Blueprint, render_template

event_bp = Blueprint('event', __name__)

@event_bp.route('/<id>')
def show(id):
 #   event = get_event()
    # create the comment form
   # cform = CommentForm()    
    return render_template('event.html')