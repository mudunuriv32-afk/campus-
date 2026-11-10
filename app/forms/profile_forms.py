from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Regexp


class ProfilePhotoUploadForm(FlaskForm):
    photo = FileField('Upload New Photo', validators=[
        FileAllowed(['png', 'jpg', 'jpeg', 'webp'], message="Only PNG, JPG, JPEG, or WEBP image formats are supported.")
    ])
    submit = SubmitField('Update Photo')


class ProfileEditForm(FlaskForm):
    phone = StringField('Contact Phone Number', validators=[
        DataRequired(message="Phone number is required."),
        Regexp(r'^\+?[\d\s\(\)-]{8,25}$', message="Enter a valid phone number.")
    ])
    submit = SubmitField('Save Profile')
