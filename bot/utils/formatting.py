def collection_text(c, category='Uncategorized'):
    desc=f'\n\n{c.get("description")}' if c.get('description') else ''
    return f'📦 <b>{c["title"]}</b>\n\n🖼 Files: {c.get("media_count",0):,}\n👁 Views: {c.get("views",0):,}\n🔓 Unlocks: {c.get("unlock_count",0):,}\n💰 Cost: {c.get("price",0):,} Tokens\n📂 Category: {category}{desc}'
