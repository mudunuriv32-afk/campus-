from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Regexp
from app.models.user import User


class LoginForm(FlaskForm):
    email = StringField('College ID / College Email', validators=[
        DataRequired(message="College ID or Email is required.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required.")
    ])
    remember_me = BooleanField('Keep me signed in')
    submit = SubmitField('Sign In')


class ChangeTemporaryPasswordForm(FlaskForm):
    temp_password = PasswordField('Temporary Password', validators=[
        DataRequired(message="Temporary password is required.")
    ])
    new_password = PasswordField('New Permanent Password', validators=[
        DataRequired(message="New password is required."),
        Length(min=8, message="Password must be at least 8 characters long.")
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message="Please confirm your new password."),
        EqualTo('new_password', message="Passwords must match.")
    ])
    submit = SubmitField('Set Permanent Password')


class StudentRegisterForm(FlaskForm):
    full_name = StringField('Full Name', validators=[
        DataRequired(message="Full name is required."),
        Length(min=3, max=100)
    ])
    email = StringField('College Email', validators=[
        DataRequired(message="Email is required."),
        Email(message="Enter a valid college email.")
    ])
    campus_id = StringField('Student ID (Roll No / PRN)', validators=[
        DataRequired(message="Student ID is required."),
        Length(min=3, max=50)
    ])
    department_id = SelectField('Department', coerce=int, validators=[
        DataRequired(message="Select your department.")
    ])
    designation_or_year = SelectField('Year of Study', choices=[
        ('1st Year Undergraduate', '1st Year Undergraduate'),
        ('2nd Year Undergraduate', '2nd Year Undergraduate'),
        ('3rd Year Undergraduate', '3rd Year Undergraduate'),
        ('4th Year Undergraduate', '4th Year Undergraduate'),
        ('Postgraduate / Master', 'Postgraduate / Master'),
        ('PhD Scholar', 'PhD Scholar')
    ], validators=[DataRequired()])
    phone = StringField('Phone Number', validators=[
        DataRequired(message="Phone number is required."),
        Regexp(r'^\+?[\d\s-]{8,20}$', message="Enter a valid phone number.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=8, message="Password must be at least 8 characters.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Register Student Account')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.lower().strip()).first()
        if user:
            raise ValidationError("This email is already registered. Please sign in or use another email.")

    def validate_campus_id(self, field):
        user = User.query.filter_by(campus_id=field.data.strip()).first()
        if user:
            raise ValidationError("This Student ID is already registered.")


class StaffRegisterForm(FlaskForm):
    full_name = StringField('Full Name', validators=[
        DataRequired(message="Full name is required."),
        Length(min=3, max=100)
    ])
    email = StringField('Official Staff Email', validators=[
        DataRequired(message="Email is required."),
        Email(message="Enter a valid official college email.")
    ])
    campus_id = StringField('Employee ID', validators=[
        DataRequired(message="Employee ID is required."),
        Length(min=3, max=50)
    ])
    department_id = SelectField('Department', coerce=int, validators=[
        DataRequired(message="Select your department.")
    ])
    designation_or_year = StringField('Designation / Office Role', validators=[
        DataRequired(message="Designation is required."),
        Length(min=2, max=50)
    ])
    phone = StringField('Official Phone / Extension', validators=[
        DataRequired(message="Phone number is required."),
        Regexp(r'^\+?[\d\s-]{8,20}$', message="Enter a valid phone number.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=8, message="Password must be at least 8 characters.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Register Staff Account')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.lower().strip()).first()
        if user:
            raise ValidationError("This email is already registered.")

    def validate_campus_id(self, field):
        user = User.query.filter_by(campus_id=field.data.strip()).first()
        if user:
            raise ValidationError("This Employee ID is already registered.")


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters.")
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message="New passwords must match.")
    ])
    submit = SubmitField('Update Password')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Registered College Email', validators=[
        DataRequired(),
        Email(message="Enter a valid email address.")
    ])
    submit = SubmitField('Send Password Reset Link')
