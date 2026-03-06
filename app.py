import os
import random
import string
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_mail import Mail, Message
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from models import db, User, Project, ProjectImage
from forms import RegistrationForm, LoginForm, VerifyForm, ProfileEditForm, ProjectForm

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')
app.config['SQLALCHEMY_DATABASE_HOST'] = os.environ.get('DB_HOST', 'db')
app.config['SQLALCHEMY_DATABASE_PORT'] = os.environ.get('DB_PORT', '5432')
app.config['SQLALCHEMY_DATABASE_USER'] = os.environ.get('DB_USER', 'postgres')
app.config['SQLALCHEMY_DATABASE_PASSWORD'] = os.environ.get('DB_PASSWORD', 'postgres')
app.config['SQLALCHEMY_DATABASE_NAME'] = os.environ.get('DB_NAME', 'portfolio_db')

# Construct Database URL
db_url = f"postgresql://{app.config['SQLALCHEMY_DATABASE_USER']}:{app.config['SQLALCHEMY_DATABASE_PASSWORD']}@{app.config['SQLALCHEMY_DATABASE_HOST']}:{app.config['SQLALCHEMY_DATABASE_PORT']}/{app.config['SQLALCHEMY_DATABASE_NAME']}"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', db_url)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail Configuration (Yandex)
app.config['MAIL_SERVER'] = 'smtp.yandex.ru'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

# Initialize Extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def send_verification_email(user):
    code = ''.join(random.choices(string.digits, k=5))
    user.verification_code = code
    user.code_expires_at = datetime.utcnow() + timedelta(minutes=5)
    db.session.commit()
    
    msg = Message('Your Verification Code',
                  recipients=[user.email])
    msg.body = f'Your verification code is: {code}. It will expire in 5 minutes.'
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# Basic Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search_users')
def search_users():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    # Remove @ if present
    if query.startswith('@'):
        query = query[1:]
        
    users = User.query.filter(User.username.ilike(f'%{query}%')).limit(5).all()
    return jsonify([{'username': u.username, 'avatar': url_for('static', filename='uploads/' + u.avatar)} for u in users])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        if send_verification_email(user):
            flash('A verification code has been sent to your email.', 'info')
            return redirect(url_for('verify', user_id=user.id))
        else:
            flash('Error sending verification email. Please try again later.', 'danger')
    return render_template('register.html', title='Register', form=form)

@app.route('/verify/<int:user_id>', methods=['GET', 'POST'])
def verify(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_verified:
        return redirect(url_for('login'))
    
    form = VerifyForm()
    if form.validate_on_submit():
        if user.code_expires_at < datetime.utcnow():
            flash('Verification code has expired. Please register again.', 'danger')
            return redirect(url_for('register'))
        
        if user.verification_code == form.code.data:
            user.is_verified = True
            user.verification_code = None
            user.code_expires_at = None
            db.session.commit()
            flash('Your account has been verified! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid verification code.', 'danger')
            
    return render_template('verify.html', title='Verify Email', form=form, user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            # Check lockout
            if user.is_locked():
                minutes_left = int((user.lockout_until - datetime.utcnow()).total_seconds() / 60) + 1
                flash(f'Account locked. Please try again in {minutes_left} minutes.', 'danger')
                return render_template('login.html', title='Login', form=form)

            if user.check_password(form.password.data):
                if not user.is_verified:
                    flash('Please verify your email first.', 'warning')
                    return redirect(url_for('verify', user_id=user.id))
                
                # Reset failed attempts on success
                user.failed_attempts = 0
                user.lockout_until = None
                db.session.commit()
                
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                # Increment failed attempts
                user.failed_attempts += 1
                if user.failed_attempts >= 5:
                    user.lockout_until = datetime.utcnow() + timedelta(minutes=5)
                    flash('Too many failed attempts. Account locked for 5 minutes.', 'danger')
                else:
                    flash('Login Unsuccessful. Please check email and password', 'danger')
                db.session.commit()
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

from werkzeug.utils import secure_filename
import uuid

# ... (existing imports)

def save_picture(form_picture, folder='uploads'):
    random_hex = uuid.uuid4().hex
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static', folder, picture_fn)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(picture_path), exist_ok=True)
    
    form_picture.save(picture_path)
    return picture_fn

@app.route('/@<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    projects = user.projects.order_by(Project.created_at.desc()).all()
    return render_template('profile.html', user=user, projects=projects)

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    main_image = project.images.filter_by(is_main=True).first()
    other_images = project.images.filter_by(is_main=False).all()
    return render_template('project_detail.html', project=project, main_image=main_image, other_images=other_images)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = ProfileEditForm()
    if form.validate_on_submit():
        if form.avatar.data:
            picture_file = save_picture(form.avatar.data)
            current_user.avatar = picture_file
        
        current_user.bio = form.bio.data
        current_user.skills = [s.strip() for s in form.skills.data.split(',') if s.strip()]
        
        # Update contacts
        contacts = {}
        if form.telegram.data: contacts['Telegram'] = form.telegram.data
        if form.github.data: contacts['GitHub'] = form.github.data
        if form.linkedin.data: contacts['LinkedIn'] = form.linkedin.data
        current_user.contacts = contacts
        
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile', username=current_user.username))
    elif request.method == 'GET':
        form.bio.data = current_user.bio
        form.skills.data = ', '.join(current_user.skills)
        form.telegram.data = current_user.contacts.get('Telegram', '')
        form.github.data = current_user.contacts.get('GitHub', '')
        form.linkedin.data = current_user.contacts.get('LinkedIn', '')
    return render_template('settings.html', title='Settings', form=form)

@app.route('/project/new', methods=['GET', 'POST'])
@login_required
def new_project():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(title=form.title.data, 
                         description=form.description.data,
                         stack=[s.strip() for s in form.stack.data.split(',') if s.strip()],
                         author=current_user)
        db.session.add(project)
        db.session.commit()
        
        files = request.files.getlist('images')
        if files:
            for i, file in enumerate(files):
                if file and file.filename:
                    picture_file = save_picture(file)
                    is_main = (i == 0) # First image is main
                    img = ProjectImage(image_path=picture_file, project=project, is_main=is_main)
                    db.session.add(img)
            db.session.commit()
            
        flash('Your project has been created!', 'success')
        return redirect(url_for('profile', username=current_user.username))
    return render_template('project_form.html', title='New Project', form=form)

@app.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.author != current_user:
        abort(403)
    
    form = ProjectForm()
    if form.validate_on_submit():
        project.title = form.title.data
        project.description = form.description.data
        project.stack = [s.strip() for s in form.stack.data.split(',') if s.strip()]
        
        files = request.files.getlist('images')
        if files and files[0].filename:
            # If new images uploaded, we can either append or replace. 
            # For now, let's append new ones.
            for file in files:
                if file and file.filename:
                    picture_file = save_picture(file)
                    # Check if project already has a main image
                    has_main = project.images.filter_by(is_main=True).first() is not None
                    img = ProjectImage(image_path=picture_file, project=project, is_main=not has_main)
                    db.session.add(img)
        
        db.session.commit()
        flash('Your project has been updated!', 'success')
        return redirect(url_for('project_detail', project_id=project.id))
    elif request.method == 'GET':
        form.title.data = project.title
        form.description.data = project.description
        form.stack.data = ', '.join(project.stack)
    
    return render_template('project_form.html', title='Edit Project', form=form, project=project)

@app.route('/project/image/<int:image_id>/delete', methods=['POST'])
@login_required
def delete_project_image(image_id):
    image = ProjectImage.query.get_or_404(image_id)
    if image.project.author != current_user:
        abort(403)
    
    project_id = image.project_id
    was_main = image.is_main
    
    # Delete file from disk
    try:
        os.remove(os.path.join(app.root_path, 'static/uploads', image.image_path))
    except:
        pass
        
    db.session.delete(image)
    
    # If we deleted the main image, set another one as main
    if was_main:
        next_image = ProjectImage.query.filter_by(project_id=project_id).first()
        if next_image:
            next_image.is_main = True
            
    db.session.commit()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
