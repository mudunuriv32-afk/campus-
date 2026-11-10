import re
from datetime import timedelta
from sqlalchemy import or_, and_, func
from app.extensions import db
from app.models.item import Item, ItemCategory


def search_items(item_type=None, keyword=None, category_id=None, location=None, date_from=None, date_to=None, status='OPEN', page=1, per_page=9):
    """
    Query items with parameterized filters, keyword search, status filter, and pagination.
    """
    query = Item.query

    if item_type in ('LOST', 'FOUND'):
        query = query.filter(Item.item_type == item_type)

    if status and status != 'ALL':
        query = query.filter(Item.status == status)
    elif status != 'ALL':
        query = query.filter(Item.status != 'CLOSED')

    if category_id:
        try:
            cat_id = int(category_id)
            query = query.filter(Item.category_id == cat_id)
        except (ValueError, TypeError):
            pass

    if location:
        query = query.filter(Item.location.ilike(f"%{location.strip()}%"))

    if date_from:
        query = query.filter(Item.incident_date >= date_from)

    if date_to:
        query = query.filter(Item.incident_date <= date_to)

    if keyword:
        kw = f"%{keyword.strip()}%"
        query = query.filter(or_(
            Item.title.ilike(kw),
            Item.description.ilike(kw),
            Item.location.ilike(kw)
        ))

    # Sort newest incident and creation date first
    query = query.order_by(Item.incident_date.desc(), Item.created_at.desc())

    return query.paginate(page=page, per_page=per_page, error_out=False)


def find_matching_suggestions(target_item: Item, limit: int = 4) -> list[dict]:
    """
    Find potential matches between a LOST item and FOUND items (or vice-versa).
    Matching criteria:
    - Opposite item_type
    - Status is OPEN
    - Same Category (highest weight)
    - Incident date within +/- 7 days
    - Common keyword overlap in title/description/location
    Returns a list of dicts: {'item': Item, 'score': int, 'reasons': list[str]}
    """
    opposite_type = 'FOUND' if target_item.item_type == 'LOST' else 'LOST'
    
    # Base candidates of opposite type and open status
    candidates = Item.query.filter(
        Item.item_type == opposite_type,
        Item.status == 'OPEN',
        Item.id != target_item.id
    ).all()

    target_words = set(re.findall(r'\w{4,}', (target_item.title + " " + target_item.description + " " + target_item.location).lower()))

    results = []
    for cand in candidates:
        score = 0
        reasons = []

        # Category match (+40 points)
        if cand.category_id == target_item.category_id:
            score += 40
            reasons.append(f"Same category ({cand.category.name if cand.category else 'Matching'})")

        # Location proximity (+25 points)
        if target_item.location and cand.location:
            t_loc = target_item.location.lower().strip()
            c_loc = cand.location.lower().strip()
            if t_loc in c_loc or c_loc in t_loc:
                score += 25
                reasons.append(f"Similar campus location: {cand.location}")

        # Date proximity (+20 points if within 7 days)
        if target_item.incident_date and cand.incident_date:
            days_diff = abs((cand.incident_date - target_item.incident_date).days)
            if days_diff <= 3:
                score += 25
                reasons.append(f"Reported within {days_diff} day(s)")
            elif days_diff <= 7:
                score += 15
                reasons.append(f"Reported within {days_diff} days")

        # Keyword token overlap (+5 points per match, up to 20)
        cand_words = set(re.findall(r'\w{4,}', (cand.title + " " + cand.description + " " + cand.location).lower()))
        common = target_words.intersection(cand_words)
        if common:
            kw_points = min(len(common) * 5, 20)
            score += kw_points
            reasons.append(f"Keywords matched: {', '.join(list(common)[:3])}")

        if score >= 35:
            results.append({
                'item': cand,
                'score': min(score, 100),
                'reasons': reasons
            })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:limit]
