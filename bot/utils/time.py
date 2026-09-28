from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc)
def day_key(): return now().date().isoformat()
def seconds_human(seconds):
    import humanize
    from datetime import timedelta
    return humanize.naturaldelta(timedelta(seconds=max(0, int(seconds))))
