from bson import ObjectId
def oid(value):
    try: return ObjectId(value)
    except Exception: return None
def positive(value):
    try: return int(value) >= 0
    except (TypeError, ValueError): return False
