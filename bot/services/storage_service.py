"""Permanent Telegram storage-channel adapter; media is never written to local disk."""
import logging

log = logging.getLogger(__name__)

class StorageService:
    def __init__(self, channel_id: int):
        self.channel_id = channel_id

    async def archive(self, app, source_message):
        """Copy a photo/video to storage and return only Telegram-origin metadata."""
        stored = await app.copy_message(
            self.channel_id, source_message.chat.id, source_message.id
        )
        media = stored.photo or stored.video
        if media is None:
            raise ValueError("storage copy did not contain photo or video")
        return {
            "storage_message_id": stored.id,
            "file_id": media.file_id,
            "media_type": "photo" if stored.photo else "video",
            "caption": stored.caption or "",
        }

    async def status(self, app):
        """Return a safe, human-readable channel permission report."""
        try:
            chat = await app.get_chat(self.channel_id)
            me = await app.get_me()
            member = await app.get_chat_member(self.channel_id, me.id)
            status = str(member.status).lower()
            privileges = getattr(member, "privileges", None)
            can_post = status in {"owner", "creator"} or bool(
                getattr(privileges, "can_post_messages", False)
            )
            if "admin" not in status and status not in {"owner", "creator"}:
                return False, f"Bot is not an administrator in {chat.title}."
            if not can_post:
                return False, f"Bot cannot post messages in {chat.title}."
            return True, f"✅ Storage channel ready: {chat.title}\nID: <code>{self.channel_id}</code>"
        except Exception:
            log.warning("Storage-channel status check failed", exc_info=True)
            return False, "❌ Storage channel is inaccessible. Add the bot as an administrator with post permissions and verify STORAGE_CHANNEL_ID."
