from flask_wtf import FlaskForm
from wtforms import StringField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Length


class CollegeIdSearchForm(FlaskForm):
    college_id = StringField('College ID / User ID', validators=[
        DataRequired(message="Please enter a College ID or Employee ID to search."),
        Length(min=2, max=50, message="ID must be between 2 and 50 characters.")
    ])
    submit = SubmitField('Search User')


class ConfirmResetForm(FlaskForm):
    user_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField('Generate Temporary Password')
