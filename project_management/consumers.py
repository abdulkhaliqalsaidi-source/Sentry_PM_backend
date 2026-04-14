import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Project, ProjectMessage
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']

        # Authenticate via JWT token in query string (more secure than username)
        query_string = self.scope['query_string'].decode('utf-8')
        from urllib.parse import parse_qs
        query_params = parse_qs(query_string)

        self.username = None

        # Try JWT token first
        token = query_params.get('token', [None])[0]
        if token:
            user = await self.get_user_from_token(token)
            if user:
                self.username = user.username
                self.user = user

        # Fallback: username param (for backward compat)
        if not self.username:
            self.username = query_params.get('username', [None])[0]
            if self.username:
                self.user = await self.get_user_by_username(self.username)

        if not self.username:
            await self.close(code=4001)
            return

        self.room_group_name = f'chat_{self.project_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Broadcast presence
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'user_presence',
            'username': self.username,
            'is_online': True
        })

    async def disconnect(self, close_code):
        if hasattr(self, 'username') and self.username:
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'user_presence',
                'username': self.username,
                'is_online': False
            })
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        event_type = data.get('type', 'message')
        username = self.username  # always use authenticated username

        if event_type == 'message':
            content    = data.get('content', '').strip()
            reply_to_id = data.get('reply_to_id')

            if not content:
                return

            message = await self.create_message(content, username, reply_to_id)
            if message:
                msg_data = await self.serialize_message(message)
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'chat_message',
                    'data': msg_data
                })

        elif event_type == 'typing':
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'user_typing',
                'username': username,
                'is_typing': data.get('is_typing', False)
            })

        elif event_type == 'delete_message':
            message_id = data.get('message_id')
            if message_id and await self.delete_message(message_id, username):
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'message_deleted',
                    'message_id': message_id
                })

        elif event_type == 'edit_message':
            message_id  = data.get('message_id')
            new_content = data.get('content', '').strip()
            if message_id and new_content and await self.edit_message(message_id, username, new_content):
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'message_edited',
                    'message_id': message_id,
                    'content': new_content
                })

        elif event_type == 'reaction':
            message_id = data.get('message_id')
            emoji      = data.get('emoji', '')
            if message_id and emoji:
                result = await self.toggle_reaction(message_id, username, emoji)
                if result is not None:
                    await self.channel_layer.group_send(self.room_group_name, {
                        'type': 'message_reaction',
                        'message_id': message_id,
                        'emoji': emoji,
                        'username': username,
                        'added': result
                    })

    # ── Group event handlers ──────────────────────────────────────

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'type': 'message', 'data': event['data']}))

    async def user_typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id']
        }))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message_id': event['message_id'],
            'content': event['content']
        }))

    async def user_presence(self, event):
        await self.send(text_data=json.dumps({
            'type': 'presence',
            'username': event['username'],
            'is_online': event['is_online']
        }))

    async def message_reaction(self, event):
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            'message_id': event['message_id'],
            'emoji': event['emoji'],
            'username': event['username'],
            'added': event['added']
        }))

    # ── DB helpers ────────────────────────────────────────────────

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from rest_framework_simplejwt.exceptions import TokenError
            access = AccessToken(token)
            return User.objects.get(id=access['user_id'])
        except Exception:
            return None

    @database_sync_to_async
    def get_user_by_username(self, username):
        return User.objects.filter(username=username).first()

    @database_sync_to_async
    def create_message(self, content, username, reply_to_id=None):
        try:
            project = Project.objects.get(id=self.project_id)
            user    = User.objects.get(username=username)
            msg     = ProjectMessage.objects.create(project=project, sender=user, content=content)
            if reply_to_id:
                reply = ProjectMessage.objects.filter(id=reply_to_id, project=project).first()
                if reply:
                    msg.reply_to = reply
                    msg.save(update_fields=['reply_to'])
            return msg
        except Exception as e:
            print(f"[Chat] Error saving message: {e}")
            return None

    @database_sync_to_async
    def serialize_message(self, message):
        # Refresh from DB to get all relations
        msg = ProjectMessage.objects.select_related(
            'sender', 'reply_to', 'reply_to__sender'
        ).get(id=message.id)

        reply_data = None
        if msg.reply_to:
            reply_data = {
                'id': msg.reply_to.id,
                'sender_username': msg.reply_to.sender.username,
                'content': msg.reply_to.content,
                'is_deleted': msg.reply_to.is_deleted,
            }

        return {
            'id': msg.id,
            'project': msg.project_id,
            'sender': msg.sender_id,
            'sender_username': msg.sender.username,
            'content': msg.content,
            'reply_to': msg.reply_to_id,
            'reply_to_details': reply_data,
            'is_deleted': msg.is_deleted,
            'is_edited': msg.is_edited,
            'attachment': msg.attachment.url if msg.attachment else None,
            'created_at': msg.created_at.isoformat(),
        }

    @database_sync_to_async
    def delete_message(self, message_id, username):
        try:
            msg = ProjectMessage.objects.get(id=message_id, sender__username=username)
            msg.is_deleted = True
            msg.content = ''
            msg.save(update_fields=['is_deleted', 'content'])
            return True
        except ProjectMessage.DoesNotExist:
            return False

    @database_sync_to_async
    def edit_message(self, message_id, username, new_content):
        try:
            msg = ProjectMessage.objects.get(id=message_id, sender__username=username)
            if msg.is_deleted:
                return False
            msg.content = new_content
            msg.is_edited = True
            msg.save(update_fields=['content', 'is_edited'])
            return True
        except ProjectMessage.DoesNotExist:
            return False

    @database_sync_to_async
    def toggle_reaction(self, message_id, username, emoji):
        """Toggle emoji reaction — returns True if added, False if removed, None on error."""
        try:
            from .models import MessageReaction
            msg  = ProjectMessage.objects.get(id=message_id)
            user = User.objects.get(username=username)
            reaction, created = MessageReaction.objects.get_or_create(
                message=msg, user=user, emoji=emoji
            )
            if not created:
                reaction.delete()
                return False
            return True
        except Exception as e:
            print(f"[Chat] Reaction error: {e}")
            return None


# ── Doc Collaboration Consumer ────────────────────────────────────────────────

class DocCollaborationConsumer(AsyncWebsocketConsumer):
    """
    Handles real-time collaboration for a single document:
    - Presence: who is currently viewing/editing
    - Live cursor / typing indicator
    - Comments: add, delete broadcast
    - Doc update notifications
    """

    async def connect(self):
        self.doc_id = self.scope['url_route']['kwargs']['doc_id']
        self.project_id = self.scope['url_route']['kwargs']['project_id']

        query_string = self.scope['query_string'].decode('utf-8')
        from urllib.parse import parse_qs
        query_params = parse_qs(query_string)

        self.username = None
        token = query_params.get('token', [None])[0]
        if token:
            user = await self.get_user_from_token(token)
            if user:
                self.username = user.username
                self.user = user

        if not self.username:
            await self.close(code=4001)
            return

        self.room_group_name = f'doc_{self.doc_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Broadcast presence join
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'doc_presence',
            'username': self.username,
            'is_online': True
        })

    async def disconnect(self, close_code):
        if hasattr(self, 'username') and self.username:
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'doc_presence',
                'username': self.username,
                'is_online': False
            })
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        event_type = data.get('type')

        if event_type == 'typing':
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'doc_typing',
                'username': self.username,
                'is_typing': data.get('is_typing', False)
            })

        elif event_type == 'add_comment':
            content = data.get('content', '').strip()
            if not content:
                return
            comment = await self.create_comment(content)
            if comment:
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'doc_comment_added',
                    'comment': comment
                })
                # Notify project members
                await self.notify_project_members(comment)

        elif event_type == 'delete_comment':
            comment_id = data.get('comment_id')
            if comment_id and await self.delete_comment(comment_id):
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'doc_comment_deleted',
                    'comment_id': comment_id
                })

        elif event_type == 'doc_updated':
            # Broadcast to others that doc was saved
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'doc_updated_broadcast',
                'username': self.username,
                'title': data.get('title', '')
            })

    # ── Group event handlers ──────────────────────────────────────

    async def doc_presence(self, event):
        await self.send(text_data=json.dumps({
            'type': 'presence',
            'username': event['username'],
            'is_online': event['is_online']
        }))

    async def doc_typing(self, event):
        if event['username'] == self.username:
            return
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    async def doc_comment_added(self, event):
        await self.send(text_data=json.dumps({
            'type': 'comment_added',
            'comment': event['comment']
        }))

    async def doc_comment_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'comment_deleted',
            'comment_id': event['comment_id']
        }))

    async def doc_updated_broadcast(self, event):
        if event['username'] == self.username:
            return
        await self.send(text_data=json.dumps({
            'type': 'doc_updated',
            'username': event['username'],
            'title': event['title']
        }))

    # ── DB helpers ────────────────────────────────────────────────

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            user_id = AccessToken(token)['user_id']
            return User.objects.get(id=user_id)
        except Exception:
            return None

    @database_sync_to_async
    def create_comment(self, content):
        try:
            from .models import Documentation, DocComment
            doc = Documentation.objects.get(id=self.doc_id)
            comment = DocComment.objects.create(document=doc, author=self.user, content=content)
            return {
                'id': comment.id,
                'author': self.username,
                'content': comment.content,
                'created_at': comment.created_at.isoformat()
            }
        except Exception as e:
            print(f"[DocCollab] Comment error: {e}")
            return None

    @database_sync_to_async
    def delete_comment(self, comment_id):
        try:
            from .models import DocComment
            DocComment.objects.get(id=comment_id, author=self.user).delete()
            return True
        except Exception:
            return False

    @database_sync_to_async
    def notify_project_members(self, comment_data):
        try:
            from .models import Documentation, ProjectRole, Notification
            doc = Documentation.objects.select_related('project').get(id=self.doc_id)
            members = ProjectRole.objects.filter(project=doc.project).select_related('user').exclude(user=self.user)
            for role in members:
                Notification.objects.create(
                    recipient=role.user,
                    actor=self.user,
                    verb=f"علّق على توثيق",
                    type='COMMENT',
                    project=doc.project
                )
        except Exception as e:
            print(f"[DocCollab] Notify error: {e}")


class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.username = self.scope['url_route']['kwargs']['username']
        self.room_group_name = f'user_notifications_{self.username}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def notification_message(self, event):
        await self.send(text_data=json.dumps({'type': 'notification', 'data': event['data']}))
