from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class ClaimSubmitForm(FlaskForm):
    claim_description = TextAreaField('Why is this item yours? (Proof Summary)', validators=[
        DataRequired(message="Please explain why you are claiming this item."),
        Length(min=10, max=1000, message="Summary must be between 10 and 1000 characters.")
    ])
    verification_details = TextAreaField('Secret / Specific Identifying Verification Details', validators=[
        DataRequired(message="Provide verifiable proof (e.g. serial numbers, wallpaper, scratch marks, unique stickers)."),
        Length(min=10, max=1500)
    ])
    proof_image = FileField('Optional Proof of Ownership Photo (Receipt, old photo, purchase email screenshot)', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Only JPG, PNG and WEBP images are allowed.')
    ])
    submit = SubmitField('Submit Claim Request')


class ClaimReviewForm(FlaskForm):
    action = SelectField('Decision', choices=[
        ('APPROVE', 'Approve Claim (Mark Item Returned)'),
        ('REJECT', 'Reject Claim')
    ], validators=[DataRequired()])
    remarks = TextAreaField('Review Remarks / Handover Instructions', validators=[
        DataRequired(message="Please provide comments or meeting instructions for the claimant."),
        Length(min=5, max=1000)
    ])
    submit = SubmitField('Submit Review Decision')
