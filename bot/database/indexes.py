async def create_indexes(db):
    specs = {
      'users': [('telegram_id', 1)], 'collections': [('created_at', -1), ('category_id', 1), ('active', 1)],
      'categories': [('active', 1)], 'collection_media': [('collection_id', 1), ('order', 1)],
      'unlocked_collections': [('user_id', 1), ('collection_id', 1)], 'saved_collections': [('user_id', 1), ('collection_id', 1)],
      'shortener_tasks': [('user_id', 1), ('shortener_id', 1), ('created_at', -1)], 'referrals': [('referrer_id', 1), ('referred_user_id', 1)],
      'cleanup_messages': [('expiration_time', 1)], 'collection_views': [('user_id', 1), ('collection_id', 1)],
    }
    unique = {'users', 'unlocked_collections', 'saved_collections', 'referrals', 'collection_views'}
    for collection, keys in specs.items():
        await db[collection].create_index(keys, unique=collection in unique)
    await db.collections.create_index('share_token', unique=True, sparse=True)
    await db.shortener_tasks.create_index('expires_at', expireAfterSeconds=0)
