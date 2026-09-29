from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc)
def as_utc(value):
    """Treat MongoDB's timezone-naive UTC datetimes as UTC before comparison."""
    if value.tzinfo is None: return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
def day_key(): return now().date().isoformat()
def seconds_human(seconds):
    import humanize
    from datetime import timedelta
    return humanize.naturaldelta(timedelta(seconds=max(0, int(seconds))))
