from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('release_note_views', __name__)
 
@bp.route('/release-notes')
@login_required
def view_notes():
    """Page for viewing release notes"""
    return render_template('release_notes.html') 