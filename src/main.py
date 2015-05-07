from flask import Flask, url_for, redirect, render_template, request
from flask.ext.sqlalchemy import SQLAlchemy

from flask.ext import superadmin, login, wtf
from flask.ext.superadmin.contrib import sqlamodel
from wtforms.fields import TextField, PasswordField
from wtforms.validators import Required, ValidationError

# Create application
app = Flask(__name__)

# Create dummy secrey key so we can use sessions
app.config['SECRET_KEY'] = '123456790'

# Create in-memory database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.sqlite'
app.config['SQLALCHEMY_ECHO'] = True
db = SQLAlchemy(app)


# Create user model. For simplicity, it will store passwords in plain text.
# Obviously that's not right thing to do in real world application.
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(64))
    name = db.Column(db.String(80))
    address = db.Column(db.String(100))
    magical = db.Column(db.Boolean)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'))
    quidditch = db.Column(db.Boolean)
    class_id = db.relationship('Classes')

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.username

class House(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    members = db.relationship('User', backref='house',
                                lazy='dynamic')

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

class Classes(db.Model):
    student = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    lesson = db.Column(db.Integer, db.ForeignKey('course.id'), primary_key=True)
    grade = db.Column(db.String(2))
    topic = db.relationship('Course')


# Define login and registration forms (for flask-login)
class LoginForm(wtf.Form):
    username = TextField(validators=[Required()])
    password = PasswordField(validators=[Required()])

    def validate_login(self, field):
        user = self.get_user()

        if user is None:
            raise ValidationError('Invalid user')

        if user.password != self.password.data:
            raise ValidationError('Invalid password')

    def get_user(self):
        return db.session.query(User).filter_by(username=self.username.data).first()


class RegistrationForm(wtf.Form):
    username = TextField(validators=[Required()])
    password = PasswordField(validators=[Required()])

    def validate_login(self, field):
        if db.session.query(User).filter_by(login=self.login.data).count() > 0:
            raise ValidationError('Duplicate username')


# Initialize flask-login
def init_login():
    login_manager = login.LoginManager()
    login_manager.setup_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)


# Create customized model view class
class MyModelView(sqlamodel.ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated()


# Create customized index view class
class MyAdminIndexView(superadmin.AdminIndexView):
    def is_accessible(self):
        return login.current_user.is_authenticated()


# Flask views
@app.route('/')
def index():
    return render_template('index.html', user=login.current_user)


@app.route('/login/', methods=('GET', 'POST'))
def login_view():
    form = LoginForm(request.form)
    if form.validate_on_submit():
        user = form.get_user()
        login.login_user(user)
        return redirect(url_for('index'))

    return render_template('form.html', form=form)


@app.route('/register/', methods=('GET', 'POST'))
def register_view():
    form = RegistrationForm(request.form)
    if form.validate_on_submit():
        user = User()

        form.populate_obj(user)

        db.session.add(user)
        db.session.commit()

        login.login_user(user)
        return redirect(url_for('index'))

    return render_template('form.html', form=form)


@app.route('/logout/')
def logout_view():
    login.logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Initialize flask-login
    init_login()

    # Create admin
    admin = superadmin.Admin(app, 'Auth', index_view=MyAdminIndexView())

    # Add view
    admin.add_view(MyModelView(User, db.session))
    admin.add_view(MyModelView(House, db.session))
    admin.add_view(MyModelView(Course, db.session))
    admin.add_view(MyModelView(Classes, db.session))

    # Create DB
    db.create_all()

    # Start app
    app.debug = True
    app.run()
