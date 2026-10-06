import re
from datetime import datetime, timedelta
from checklist.engine import DEADLINE_PATTERNS

def resolve_deadline(raw: str, now: datetime) -> datetime | None:
    raw_lower = raw.lower()
    
    # 1. Check delay
    match = re.search(DEADLINE_PATTERNS['delay'], raw_lower, re.IGNORECASE)
    if match:
        if match.group(1):
            val = int(match.group(1))
            unit = match.group(2)
        else:
            val = int(match.group(3))
            unit = match.group(4)
            
        if unit.startswith('h'):
            return now + timedelta(hours=val)
        else:
            return now + timedelta(days=val)
            
    # 2. Check tonight
    if re.search(DEADLINE_PATTERNS['tonight'], raw_lower, re.IGNORECASE):
        return now.replace(hour=20, minute=0, second=0, microsecond=0)
        
    # 3. Check tomorrow
    if re.search(DEADLINE_PATTERNS['tomorrow'], raw_lower, re.IGNORECASE):
        return (now + timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
        
    # 4. Check monday
    if re.search(DEADLINE_PATTERNS['monday'], raw_lower, re.IGNORECASE):
        days_ahead = 0 - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return (now + timedelta(days=days_ahead)).replace(hour=18, minute=0, second=0, microsecond=0)
        
    # 5. Check friday
    if re.search(DEADLINE_PATTERNS['friday'], raw_lower, re.IGNORECASE):
        days_ahead = 4 - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return (now + timedelta(days=days_ahead)).replace(hour=18, minute=0, second=0, microsecond=0)
        
    # 6. Check next_week
    if re.search(DEADLINE_PATTERNS['next_week'], raw_lower, re.IGNORECASE):
        days_ahead = 0 - now.weekday()
        days_ahead += 7
        return (now + timedelta(days=days_ahead)).replace(hour=18, minute=0, second=0, microsecond=0)
        
    # 7. Check date
    match = re.search(DEADLINE_PATTERNS['date'], raw_lower, re.IGNORECASE)
    if match:
        date_str = match.group(1).replace('-', '/')
        parts = date_str.split('/')
        day = int(parts[0])
        month = int(parts[1])
        year = now.year
        if len(parts) == 3:
            year = int(parts[2])
            if year < 100:
                year += 2000
        
        try:
            target = now.replace(year=year, month=month, day=day, hour=18, minute=0, second=0, microsecond=0)
            # Si on donne un jour/mois déjà passé cette année, on assume l'année prochaine
            if target < now and len(parts) == 2:
                target = target.replace(year=year + 1)
            return target
        except ValueError:
            return None
            
    return None
