from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, MultipleFileField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
import re

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        if not re.match(r'^[a-zA-Z0-9_]+$', username.data):
            raise ValidationError('Username can only contain English letters, numbers, and underscores.')
        
        from models import User
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        from models import User
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class VerifyForm(FlaskForm):
    code = StringField('Verification Code', validators=[DataRequired(), Length(min=5, max=5)])
    submit = SubmitField('Verify')

class ProfileEditForm(FlaskForm):
    avatar = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    bio = TextAreaField('About Me', validators=[Length(max=500)])
    skills = StringField('Skills (comma separated)', render_kw={"placeholder": "Python, Flask, Docker"})
    telegram = StringField('Telegram URL', render_kw={"placeholder": "https://t.me/username"})
    github = StringField('GitHub URL', render_kw={"placeholder": "https://github.com/username"})
    linkedin = StringField('LinkedIn URL', render_kw={"placeholder": "https://linkedin.com/in/username"})
    submit = SubmitField('Save Changes')

class ProjectForm(FlaskForm):
    title = StringField('Project Title', validators=[DataRequired(), Length(max=128)])
    description = TextAreaField('Description', validators=[DataRequired()])
    stack = StringField('Tech Stack (comma separated)', render_kw={"placeholder": "PostgreSQL, Bootstrap"})
    images = MultipleFileField('Project Images', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Save Project')
