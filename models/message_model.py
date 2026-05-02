from supabase import create_client
import os


class MessageModel:
    def __init__(self):
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )

    # ── Conversations ─────────────────────────────────────────

    def get_or_create_conversation(self, user_a, user_b, order_id=None):
        """Return existing conversation or create one. Canonical order: smaller UUID first."""
        p1, p2 = sorted([user_a, user_b])
        query = (
            self.supabase.table('conversations')
            .select('*')
            .eq('participant_1', p1)
            .eq('participant_2', p2)
        )
        if order_id:
            query = query.eq('order_id', order_id)
        else:
            query = query.is_('order_id', 'null')
        result = query.limit(1).execute()
        if result.data:
            return result.data[0]
        payload = {'participant_1': p1, 'participant_2': p2}
        if order_id:
            payload['order_id'] = order_id
        created = self.supabase.table('conversations').insert(payload).execute()
        return created.data[0] if created.data else None

    def get_conversations_for_user(self, user_id):
        """All conversations where user is a participant, newest first."""
        r1 = self.supabase.table('conversations').select(
            '*, other:participant_2(id, first_name, last_name, role, profile_picture)'
        ).eq('participant_1', user_id).order('updated_at', desc=True).execute()

        r2 = self.supabase.table('conversations').select(
            '*, other:participant_1(id, first_name, last_name, role, profile_picture)'
        ).eq('participant_2', user_id).order('updated_at', desc=True).execute()

        convs = (r1.data or []) + (r2.data or [])
        # Attach unread count per conversation
        for c in convs:
            unread = self.supabase.table('messages').select('id', count='exact') \
                .eq('conversation_id', c['id']) \
                .eq('receiver_id', user_id) \
                .eq('is_read', False).execute()
            c['unread_count'] = unread.count or 0
        convs.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        return convs

    def get_all_conversations(self):
        """Admin: all conversations with both participant details."""
        result = self.supabase.table('conversations').select(
            '*, p1:participant_1(id, first_name, last_name, role), p2:participant_2(id, first_name, last_name, role)'
        ).order('updated_at', desc=True).execute()
        rows = result.data or []
        for c in rows:
            unread = self.supabase.table('messages').select('id', count='exact') \
                .eq('conversation_id', c['id']).eq('is_read', False).execute()
            c['unread_count'] = unread.count or 0
        return rows

    def get_conversation_by_id(self, conv_id):
        result = self.supabase.table('conversations').select('*').eq('id', conv_id).limit(1).execute()
        return result.data[0] if result.data else None

    # ── Messages ──────────────────────────────────────────────

    def get_messages(self, conversation_id, limit=50):
        result = self.supabase.table('messages').select(
            '*, sender:sender_id(id, first_name, last_name, role, profile_picture)'
        ).eq('conversation_id', conversation_id).order('created_at', desc=False).limit(limit).execute()
        return result.data or []

    def send_message(self, conversation_id, sender_id, receiver_id, content, attachment_url=None):
        payload = {
            'conversation_id': conversation_id,
            'sender_id':       sender_id,
            'receiver_id':     receiver_id,
            'content':         content.strip(),
        }
        if attachment_url:
            payload['attachment_url'] = attachment_url
        result = self.supabase.table('messages').insert(payload).execute()
        if not result.data:
            return None
        msg = result.data[0]
        # Update conversation last_message + updated_at
        self.supabase.table('conversations').update({
            'last_message': content[:100],
            'updated_at':   msg['created_at']
        }).eq('id', conversation_id).execute()
        return msg

    def mark_read(self, conversation_id, user_id):
        """Mark all messages in a conversation as read for this user."""
        self.supabase.table('messages').update({'is_read': True}) \
            .eq('conversation_id', conversation_id) \
            .eq('receiver_id', user_id) \
            .eq('is_read', False).execute()

    def get_unread_count(self, user_id):
        result = self.supabase.table('messages').select('id', count='exact') \
            .eq('receiver_id', user_id).eq('is_read', False).execute()
        return result.count or 0

    def get_new_messages(self, conversation_id, after_id):
        """Poll: return messages newer than after_id."""
        # Get the created_at of after_id first
        ref = self.supabase.table('messages').select('created_at').eq('id', after_id).limit(1).execute()
        if not ref.data:
            return self.get_messages(conversation_id, 50)
        after_ts = ref.data[0]['created_at']
        result = self.supabase.table('messages').select(
            '*, sender:sender_id(id, first_name, last_name, role, profile_picture)'
        ).eq('conversation_id', conversation_id).gt('created_at', after_ts) \
         .order('created_at', desc=False).execute()
        return result.data or []

    def auto_message_sent(self, conversation_id, sender_id):
        """Check if sender already sent the auto welcome message in this conversation."""
        result = self.supabase.table('messages').select('id', count='exact') \
            .eq('conversation_id', conversation_id) \
            .eq('sender_id', sender_id).execute()
        return (result.count or 0) > 0

    def user_can_access(self, conversation_id, user_id, is_admin=False):
        if is_admin:
            return True
        conv = self.get_conversation_by_id(conversation_id)
        if not conv:
            return False
        return user_id in (conv['participant_1'], conv['participant_2'])
