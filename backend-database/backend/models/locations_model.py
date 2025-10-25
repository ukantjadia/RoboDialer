from models.user_model import db

class Location(db.Model):
    __tablename__ = 'locations'

    id = db.Column(db.Integer, primary_key=True)
    city_original = db.Column(db.String(128), nullable=False)
    state_code = db.Column(db.String(16), nullable=False)
    state_original = db.Column(db.String(128), nullable=False)
    country = db.Column(db.String(128), nullable=True)