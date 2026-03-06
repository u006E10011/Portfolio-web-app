from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, MultipleFileField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
import re

class RegistrationForm(FlaskForm):
    # ... (existing code)
    pass

# ... (other forms)

class ProfileEditForm(FlaskForm):
    avatar = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    bio = TextAreaField('About Me', validators=[Length(max=500)])
    skills = StringField('Skills (comma separated)', placeholder="Python, Flask, Docker")
    telegram = StringField('Telegram URL', placeholder="https://t.me/username")
    github = StringField('GitHub URL', placeholder="https://github.com/username")
    linkedin = StringField('LinkedIn URL', placeholder="https://linkedin.com/in/username")
    submit = SubmitField('Save Changes')

class ProjectForm(FlaskForm):
    title = StringField('Project Title', validators=[DataRequired(), Length(max=128)])
    description = TextAreaField('Description', validators=[DataRequired()])
    stack = StringField('Tech Stack (comma separated)', placeholder="PostgreSQL, Bootstrap")
    images = MultipleFileField('Project Images', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Save Project')
