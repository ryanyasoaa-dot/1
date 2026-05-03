from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models.message_model import MessageModel

messages_bp = Blueprint('messages', __name__, url_prefix='/messages')
msg_model = MessageModel()


def _login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def _current_user():
    return session.get('user', {})


def _is_admin():
    return _current_user().get('role') == 'admin'


# ── Pages ─────────────────────────────────────────────────────

@messages_bp.route('/')
@_login_required
def inbox():
    return render_template('messages/chat.html')


@messages_bp.route('/admin')
@_login_required
def admin_inbox():
    if not _is_admin():
        return redirect(url_for('messages.inbox'))
    return render_template('messages/admin_chat.html')


# ── API: Conversations ────────────────────────────────────────

@messages_bp.route('/api/conversations', methods=['GET'])
@_login_required
def api_conversations():
    user = _current_user()
    if _is_admin():
        convs = msg_model.get_all_conversations()
    else:
        convs = msg_model.get_conversations_for_user(user['id'])
    return jsonify(convs)


@messages_bp.route('/api/conversations/start', methods=['POST'])
@_login_required
def api_start_conversation():
    user = _current_user()
    data = request.get_json() or {}
    other_id = data.get('user_id')
    order_id = data.get('order_id')
    if not other_id:
        return jsonify({'error': 'user_id is required'}), 400
    if other_id == user['id']:
        return jsonify({'error': 'Cannot message yourself'}), 400
    conv = msg_model.get_or_create_conversation(user['id'], other_id, order_id)
    if not conv:
        return jsonify({'error': 'Failed to create conversation'}), 500
    return jsonify(conv)


@messages_bp.route('/api/conversations/find', methods=['GET'])
@_login_required
def api_find_conversation():
    """Find existing conversation between current user and another user, optionally by order_id."""
    user = _current_user()
    other_id = request.args.get('user_id')
    order_id = request.args.get('order_id')
    if not other_id:
        return jsonify({'error': 'user_id is required'}), 400
    if other_id == user['id']:
        return jsonify({'error': 'Cannot message yourself'}), 400
    
    p1, p2 = sorted([user['id'], other_id])
    query = msg_model.supabase.table('conversations').select('*').eq('participant_1', p1).eq('participant_2', p2)
    if order_id:
        query = query.eq('order_id', order_id)
    else:
        query = query.is_('order_id', 'null')
    result = query.limit(1).execute()
    return jsonify(result.data[0] if result.data else None)


@messages_bp.route('/api/conversations/<conv_id>/messages', methods=['GET'])
@_login_required
def api_get_messages(conv_id):
    user = _current_user()
    if not msg_model.user_can_access(conv_id, user['id'], _is_admin()):
        return jsonify({'error': 'Unauthorized'}), 403
    after_id = request.args.get('after')
    if after_id:
        msgs = msg_model.get_new_messages(conv_id, after_id)
    else:
        msgs = msg_model.get_messages(conv_id)
    msg_model.mark_read(conv_id, user['id'])
    return jsonify(msgs)


@messages_bp.route('/api/conversations/<conv_id>/messages', methods=['POST'])
@_login_required
def api_send_message(conv_id):
    user = _current_user()
    if not msg_model.user_can_access(conv_id, user['id'], _is_admin()):
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'error': 'Message content is required'}), 400

    conv = msg_model.get_conversation_by_id(conv_id)
    if not conv:
        return jsonify({'error': 'Conversation not found'}), 404

    # Determine receiver: the other participant
    sender_id = user['id']
    receiver_id = conv['participant_2'] if conv['participant_1'] == sender_id else conv['participant_1']

    msg = msg_model.send_message(conv_id, sender_id, receiver_id, content, data.get('attachment_url'))
    if not msg:
        return jsonify({'error': 'Failed to send message'}), 500
    return jsonify(msg), 201


@messages_bp.route('/api/conversations/<conv_id>/read', methods=['POST'])
@_login_required
def api_mark_read(conv_id):
    user = _current_user()
    if not msg_model.user_can_access(conv_id, user['id'], _is_admin()):
        return jsonify({'error': 'Unauthorized'}), 403
    msg_model.mark_read(conv_id, user['id'])
    return jsonify({'success': True})


# ── API: Unread count ─────────────────────────────────────────

@messages_bp.route('/api/unread-count', methods=['GET'])
@_login_required
def api_unread_count():
    count = msg_model.get_unread_count(_current_user()['id'])
    return jsonify({'count': count})


# ── API: Quick message (any role → any role per order) ────────

QUICK_MSG = "Thank you for your order! We are currently processing your items. We will update you once it is ready for pickup."

@messages_bp.route('/api/quick-message', methods=['POST'])
@_login_required
def api_quick_message():
    """Start or reuse a conversation and optionally send the welcome auto-message.
    Body: { other_id, order_id, send_auto: bool }
    Returns: { conversation_id, already_sent, message?, other_user: {first_name, last_name} }
    
    Note: This is a generic endpoint for any role-to-role messaging.
    """
    user = _current_user()
    data = request.get_json() or {}
    other_id = data.get('other_id') or data.get('buyer_id')  # Support both old and new param names
    order_id = data.get('order_id')
    send_auto = data.get('send_auto', False)

    if not other_id or not order_id:
        return jsonify({'error': 'other_id and order_id are required'}), 400
    if other_id == user['id']:
        return jsonify({'error': 'Cannot message yourself'}), 400

    conv = msg_model.get_or_create_conversation(user['id'], other_id, order_id)
    if not conv:
        return jsonify({'error': 'Failed to create conversation'}), 500

    conv_id = conv['id']
    already_sent = msg_model.auto_message_sent(conv_id, user['id'])

    sent_msg = None
    if send_auto and not already_sent:
        sender_id   = user['id']
        receiver_id = other_id
        sent_msg = msg_model.send_message(conv_id, sender_id, receiver_id, QUICK_MSG)

    # Fetch other user info for display
    other_user = msg_model.supabase.table('users').select('id, first_name, last_name, profile_picture, role').eq('id', other_id).single().execute()
    other_data = other_user.data if other_user.data else {}

    return jsonify({
        'conversation_id': conv_id,
        'already_sent':    already_sent,
        'message':         sent_msg,
        'other_user':           other_data,
    })


# ── Flutter-ready aliases ─────────────────────────────────────

@messages_bp.route('/api/messages', methods=['GET'])
@_login_required
def api_messages_list():
    """Flutter: GET /messages/api/messages?conversation_id=xxx"""
    conv_id = request.args.get('conversation_id')
    if not conv_id:
        return jsonify({'error': 'conversation_id required'}), 400
    return api_get_messages(conv_id)


@messages_bp.route('/api/messages', methods=['POST'])
@_login_required
def api_messages_send():
    """Flutter: POST /messages/api/messages"""
    data = request.get_json() or {}
    conv_id = data.get('conversation_id')
    if not conv_id:
        return jsonify({'error': 'conversation_id required'}), 400
    return api_send_message(conv_id)
