from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
import os

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Set the FLASK_APP environment variable
os.environ['FLASK_APP'] = 'app.py'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    expenses = db.relationship('Expense', backref='user', lazy=True)
    groups = db.relationship('Group', secondary='group_members', back_populates='members')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    members = db.relationship('User', secondary='group_members', back_populates='groups')
    expenses = db.relationship('Expense', backref='group', lazy=True)

group_members = db.Table('group_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'), primary_key=True)
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/create_group', methods=['GET', 'POST'])
@login_required
def create_group():
    if request.method == 'POST':
        group_name = request.form['group_name']
        new_group = Group(name=group_name)
        new_group.members.append(current_user)
        db.session.add(new_group)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('create_group.html')

@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        group_id = request.form.get('group_id')
        
        new_expense = Expense(
            description=description, 
            amount=amount, 
            date=datetime.utcnow(), 
            user=current_user,
            group_id=group_id
        )
        
        db.session.add(new_expense)
        db.session.commit()
        return redirect(url_for('dashboard'))
    
    groups = current_user.groups
    return render_template('add_expense.html', groups=groups)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
