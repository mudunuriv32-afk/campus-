from datetime import datetime, timezone
from app.extensions import db
from app.models.claim import Claim
from app.models.item import Item
from app.models.audit import AuditLog
from app.services.notification_service import send_notification


def submit_claim(item_id: int, claimant_id: int, claim_description: str, verification_details: str, proof_image: str = None) -> tuple[bool, str, Claim | None]:
    """
    Submit a claim for an item with duplicate-check protection.
    """
    item = Item.query.get(item_id)
    if not item:
        return False, "Item not found.", None

    if item.status in ('RETURNED', 'CLOSED'):
        return False, f"This item is already {item.status.lower()} and cannot be claimed.", None

    if item.reporter_id == claimant_id:
        return False, "You cannot submit a claim on an item you reported yourself.", None

    # Check for existing active claim by this user on this item
    existing = Claim.query.filter_by(
        item_id=item_id,
        claimant_id=claimant_id,
        status='PENDING'
    ).first()
    if existing:
        return False, "You already have a pending claim for this item.", None

    claim = Claim(
        item_id=item_id,
        claimant_id=claimant_id,
        claim_description=claim_description.strip(),
        verification_details=verification_details.strip(),
        proof_image=proof_image,
        status='PENDING'
    )
    db.session.add(claim)

    # Update item status to CLAIM_PENDING if currently OPEN
    if item.status == 'OPEN':
        item.status = 'CLAIM_PENDING'

    # Notify item reporter
    send_notification(
        user_id=item.reporter_id,
        title="New Claim Submitted",
        message=f"A new claim was submitted for your item '{item.title}'. Please review the claim details.",
        link_url=f"/claims/review/{claim.id}",
        notification_type="CLAIM_SUBMITTED"
    )

    db.session.commit()
    return True, "Claim submitted successfully.", claim


def approve_claim(claim_id: int, reviewer_id: int, remarks: str = None, ip_address: str = None) -> tuple[bool, str]:
    """
    Transactionally approve a claim, close conflicting claims, mark item as RETURNED,
    log audit, and notify all parties.
    """
    claim = Claim.query.get(claim_id)
    if not claim:
        return False, "Claim not found."

    if claim.status != 'PENDING':
        return False, f"Claim cannot be approved because its current status is {claim.status}."

    item = claim.item
    now = datetime.now(timezone.utc)

    try:
        # 1. Update this claim
        claim.status = 'APPROVED'
        claim.reviewer_id = reviewer_id
        claim.review_remarks = remarks
        claim.reviewed_at = now

        # 2. Update item status to RETURNED
        item.status = 'RETURNED'
        item.updated_at = now

        # 3. Reject other pending claims for this item
        other_claims = Claim.query.filter(
            Claim.item_id == item.id,
            Claim.id != claim.id,
            Claim.status == 'PENDING'
        ).all()

        for other in other_claims:
            other.status = 'REJECTED'
            other.reviewer_id = reviewer_id
            other.review_remarks = "Item has been successfully claimed and returned to another claimant."
            other.reviewed_at = now
            send_notification(
                user_id=other.claimant_id,
                title="Claim Update",
                message=f"Your claim on '{item.title}' was closed because the item was verified and returned to another claimant.",
                link_url=f"/claims/my-claims",
                notification_type="CLAIM_REJECTED"
            )

        # 4. Notify approved claimant
        send_notification(
            user_id=claim.claimant_id,
            title="Claim Approved! 🎉",
            message=f"Congratulations! Your claim on '{item.title}' has been APPROVED. Please check your claims page for recovery instructions.",
            link_url=f"/claims/my-claims",
            notification_type="CLAIM_APPROVED"
        )

        # 5. Audit log
        AuditLog.log(
            action='CLAIM_APPROVED',
            user_id=reviewer_id,
            target_type='Claim',
            target_id=claim.id,
            ip_address=ip_address,
            details=f"Approved claim #{claim.id} for item #{item.id} ('{item.title}'). Item marked RETURNED."
        )

        db.session.commit()
        return True, "Claim approved successfully! The item has been marked as RETURNED."
    except Exception as e:
        db.session.rollback()
        return False, f"Transaction failed: {str(e)}"


def reject_claim(claim_id: int, reviewer_id: int, remarks: str, ip_address: str = None) -> tuple[bool, str]:
    """
    Reject a claim with required reason/remarks.
    """
    claim = Claim.query.get(claim_id)
    if not claim:
        return False, "Claim not found."

    if claim.status != 'PENDING':
        return False, f"Claim cannot be rejected because its current status is {claim.status}."

    now = datetime.now(timezone.utc)
    claim.status = 'REJECTED'
    claim.reviewer_id = reviewer_id
    claim.review_remarks = remarks
    claim.reviewed_at = now

    item = claim.item
    # If no other pending claims, revert item status back to OPEN
    remaining_pending = Claim.query.filter(
        Claim.item_id == item.id,
        Claim.id != claim.id,
        Claim.status == 'PENDING'
    ).count()
    if remaining_pending == 0 and item.status == 'CLAIM_PENDING':
        item.status = 'OPEN'

    # Notify claimant
    send_notification(
        user_id=claim.claimant_id,
        title="Claim Status Update",
        message=f"Your claim on '{item.title}' was reviewed and not accepted. Reason: {remarks}",
        link_url="/claims/my-claims",
        notification_type="CLAIM_REJECTED"
    )

    # Audit log
    AuditLog.log(
        action='CLAIM_REJECTED',
        user_id=reviewer_id,
        target_type='Claim',
        target_id=claim.id,
        ip_address=ip_address,
        details=f"Rejected claim #{claim.id} for item #{item.id}. Reason: {remarks}"
    )

    db.session.commit()
    return True, "Claim rejected."
