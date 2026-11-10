from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, DateField, TimeField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class ItemReportForm(FlaskForm):
    title = StringField('Item Title / Name', validators=[
        DataRequired(message="Title is required."),
        Length(min=3, max=150, message="Title must be between 3 and 150 characters.")
    ])
    category_id = SelectField('Category', coerce=int, validators=[
        DataRequired(message="Please select a category.")
    ])
    description = TextAreaField('Detailed Description', validators=[
        DataRequired(message="Please provide a clear description of the item."),
        Length(min=10, max=2000, message="Description must be between 10 and 2000 characters.")
    ])
    identifying_features = TextAreaField('Distinctive / Private Identifying Features (Used to verify claims)', validators=[
        Optional(),
        Length(max=1000)
    ])
    location = StringField('Campus Location', validators=[
        DataRequired(message="Location where the item was lost/found is required."),
        Length(min=2, max=150)
    ])
    incident_date = DateField('Date Lost or Found', validators=[
        DataRequired(message="Date is required.")
    ])
    incident_time = TimeField('Approximate Time (Optional)', validators=[
        Optional()
    ])
    contact_preference = SelectField('Preferred Contact Method', choices=[
        ('IN_APP', 'In-App Messaging & Portal Claims (Recommended)'),
        ('EMAIL', 'College Email'),
        ('PHONE', 'Phone Call / SMS')
    ], default='IN_APP', validators=[DataRequired()])
    image = FileField('Item Photo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Only JPG, PNG and WEBP images are allowed.')
    ])
    submit = SubmitField('Submit Report')


class ItemSearchForm(FlaskForm):
    keyword = StringField('Keyword Search', validators=[Optional()])
    category_id = SelectField('Category', coerce=str, validators=[Optional()])
    location = StringField('Location', validators=[Optional()])
    date_from = DateField('From Date', validators=[Optional()])
    date_to = DateField('To Date', validators=[Optional()])
    submit = SubmitField('Apply Filters')


class FlagReportForm(FlaskForm):
    reason = TextAreaField('Reason for reporting this listing', validators=[
        DataRequired(message="Please provide a reason for moderation."),
        Length(min=5, max=500)
    ])
    submit = SubmitField('Submit Flag')
