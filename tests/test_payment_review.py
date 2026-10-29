import asyncio
import sys
import types
from copy import deepcopy
from types import SimpleNamespace

# The workspace test runtime does not ship production dependencies. Stub only
# their small interfaces so this test never connects to Telegram or MongoDB.
errors = types.ModuleType('pymongo.errors')
class DuplicateKeyError(Exception): pass
errors.DuplicateKeyError = DuplicateKeyError
pymongo = types.ModuleType('pymongo'); pymongo.__path__ = []
sys.modules.setdefault('pymongo', pymongo)
sys.modules.setdefault('pymongo.errors', errors)

bson = types.ModuleType('bson')
bson.ObjectId = lambda value: value
sys.modules.setdefault('bson', bson)

pyrogram = types.ModuleType('pyrogram'); pyrogram.__path__ = []
pyrogram_types = types.ModuleType('pyrogram.types')
class Button:
    def __init__(self, text, callback_data=None, url=None):
        self.text, self.callback_data, self.url = text, callback_data, url
class Markup:
    def __init__(self, inline_keyboard): self.inline_keyboard = inline_keyboard
pyrogram_types.InlineKeyboardButton = Button
pyrogram_types.InlineKeyboardMarkup = Markup
sys.modules.setdefault('pyrogram', pyrogram)
sys.modules.setdefault('pyrogram.types', pyrogram_types)

from bot.services.app_service import AppService
from bot.services.token_service import TokenService

PAYMENT_ID = '0123456789abcdef01234567'

class PaymentRequests:
    def __init__(self):
        self.doc = {'_id': PAYMENT_ID, 'user_id': 42, 'tokens': 100, 'rupees': 50, 'status': 'pending'}
    async def find_one_and_update(self, query, update, return_document=False):
        if self.doc['_id'] != query['_id'] or self.doc['status'] != query['status']:
            return None
        self.doc.update(update.get('$set', {}))
        for key in update.get('$unset', {}): self.doc.pop(key, None)
        return deepcopy(self.doc)
    async def find_one(self, query):
        return deepcopy(self.doc) if self.doc['_id'] == query['_id'] and self.doc['status'] == query['status'] else None

class Users:
    def __init__(self): self.doc = {'telegram_id': 42, 'balance': 7, 'total_earned': 7, 'credited_payment_ids': []}
    async def update_one(self, query, update):
        if self.doc['telegram_id'] != query['telegram_id'] or str(query['credited_payment_ids']['$ne']) in self.doc['credited_payment_ids']:
            return SimpleNamespace(matched_count=0, modified_count=0)
        self.doc['balance'] += update['$inc']['balance']
        self.doc['total_earned'] += update['$inc']['total_earned']
        self.doc['credited_payment_ids'].append(update['$addToSet']['credited_payment_ids'])
        return SimpleNamespace(matched_count=1, modified_count=1)
    async def find_one(self, query): return deepcopy(self.doc)

class Transactions:
    def __init__(self): self.rows, self.fail_next = {}, False
    async def update_one(self, query, update, upsert=False):
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError('simulated ledger write failure')
        self.rows.setdefault(query['idempotency_key'], update['$setOnInsert'])

class BroadcastCursor:
    def __init__(self, users): self.users, self.size = users, None
    def sort(self, key, direction):
        assert (key, direction) == ('telegram_id', 1)
        return self
    def batch_size(self, size): self.size = size; return self
    def __aiter__(self): return self._iterate()
    async def _iterate(self):
        assert self.size == 100
        for user in self.users: yield user

class BroadcastUsers:
    def find(self, query, projection):
        assert query == {} and projection == {'telegram_id': 1}
        return BroadcastCursor([{'telegram_id': uid} for uid in range(1000, 1205)])

class AdminSessions:
    def __init__(self): self.doc = {'_id': 'broadcast-1', 'admin_id': 1, 'kind': 'broadcast', 'step': 'confirm', 'text': 'test broadcast'}
    async def find_one(self, query): return deepcopy(self.doc)
    async def delete_one(self, query): self.doc = None

class Telegram:
    def __init__(self): self.notifications, self.broadcasts = [], []
    async def send_message(self, user_id, text, **kwargs):
        if user_id == 42: self.notifications.append((user_id, text))
        else: self.broadcasts.append((user_id, text))

class Message:
    photo = None
    async def edit_reply_markup(self, reply_markup=None): pass
    async def edit_text(self, text, reply_markup=None): self.text = text

class Query:
    def __init__(self, admin_id):
        self.from_user = SimpleNamespace(id=admin_id)
        self.message = Message()
        self.answers = []
    async def answer(self, text, show_alert=False): self.answers.append((text, show_alert))

async def verify():
    payment_requests = PaymentRequests()
    users = Users()
    transactions = Transactions()
    app = Telegram()
    service = object.__new__(AppService)
    service.db = SimpleNamespace(payment_requests=payment_requests)
    service.app = app
    service.tokens = TokenService(SimpleNamespace(users=users, token_transactions=transactions))

    first_admin = Query(1)
    await service.review_payment(first_admin, PAYMENT_ID, 'approve')
    assert payment_requests.doc['status'] == 'approved'
    assert users.doc['balance'] == 107
    assert users.doc['total_earned'] == 107
    assert len(transactions.rows) == 1
    assert len(app.notifications) == 1

    # A second admin may still see the stale button, but cannot reverse or
    # repeat the decision, credit, or user notification.
    second_admin = Query(2)
    await service.review_payment(second_admin, PAYMENT_ID, 'reject')
    assert payment_requests.doc['status'] == 'approved'
    assert users.doc['balance'] == 107
    assert len(transactions.rows) == 1

    # If the balance update succeeds but the ledger write fails, a retry must
    # repair the ledger without applying the balance increment a second time.
    retry_users = Users()
    retry_transactions = Transactions(); retry_transactions.fail_next = True
    retry_tokens = TokenService(SimpleNamespace(users=retry_users, token_transactions=retry_transactions))
    try:
        await retry_tokens.credit_payment(42, 'fedcba9876543210fedcba98', 25, 'simulated')
    except RuntimeError:
        pass
    else:
        raise AssertionError('the simulated ledger failure was not raised')
    assert retry_users.doc['balance'] == 32
    await retry_tokens.credit_payment(42, 'fedcba9876543210fedcba98', 25, 'simulated retry')
    assert retry_users.doc['balance'] == 32
    assert len(retry_transactions.rows) == 1
    assert len(app.notifications) == 1
    assert second_admin.answers[-1][1] is True

    # Replaying a credit after a ledger-write retry does not increment twice.
    await service.tokens.credit_payment(42, PAYMENT_ID, 100, 'retry')
    assert users.doc['balance'] == 107
    assert len(transactions.rows) == 1

    # Broadcast dispatch streams recipients in sorted 100-user database
    # batches and reaches all pages without materializing the whole collection.
    service.db = SimpleNamespace(admin_sessions=AdminSessions(), users=BroadcastUsers())
    broadcast_admin = Query(1)
    await service.broadcast_confirm(broadcast_admin, 'send')
    assert len(app.broadcasts) == 205
    assert app.broadcasts[0] == (1000, 'test broadcast')
    assert app.broadcasts[-1] == (1204, 'test broadcast')
    assert 'Delivered: 205' in broadcast_admin.message.text

    # Rejection finalizes without touching the user wallet or payment ledger.
    rejected_requests = PaymentRequests(); rejected_requests.doc['status'] = 'pending'
    rejected_users = Users(); rejected_transactions = Transactions(); rejected_app = Telegram()
    reject_service = object.__new__(AppService)
    reject_service.db = SimpleNamespace(payment_requests=rejected_requests)
    reject_service.app = rejected_app
    reject_service.tokens = TokenService(SimpleNamespace(users=rejected_users, token_transactions=rejected_transactions))
    await reject_service.review_payment(Query(3), PAYMENT_ID, 'reject')
    assert rejected_requests.doc['status'] == 'rejected'
    assert rejected_users.doc['balance'] == 7
    assert rejected_transactions.rows == {}
    assert len(rejected_app.notifications) == 1

asyncio.run(verify())
