from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/projects/(?P<project_id>\w+)/chat/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/notifications/(?P<username>[\w.@+-]+)/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/projects/(?P<project_id>\w+)/docs/(?P<doc_id>\w+)/$', consumers.DocCollaborationConsumer.as_asgi()),
]
