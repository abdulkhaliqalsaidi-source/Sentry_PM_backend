from rest_framework import serializers
from .models import Issue, Event, Session, User, Project, PermissionGroup

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name']

class PermissionGroupSerializer(serializers.ModelSerializer):
    user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PermissionGroup
        fields = [
            'id', 'name', 'user_count',
            'can_view_dashboard', 'can_view_issues', 'can_view_users', 'can_view_settings',
            'can_delete_issues',
            'can_create_project', 'can_edit_project', 'can_delete_project',
            'can_create_task', 'can_edit_task', 'can_delete_task',
            'can_view_user_projects',
            'can_view_backlog', 'can_view_reports',
            'can_view_members', 'can_manage_members',
            'can_view_chat',
            'can_view_docs', 'can_create_doc', 'can_edit_doc', 'can_delete_doc',
            'can_manage_releases',
            'can_view_evaluations', 'can_manage_evaluations',
            'can_view_performance', 'can_view_notifications', 'can_manage_permissions',
            'can_manage_sprints', 'can_manage_epics',
        ]

class UserSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='primary_project.name', read_only=True)
    project_id = serializers.IntegerField(source='primary_project.id', read_only=True)
    group_name = serializers.CharField(source='permission_group.name', read_only=True)
    group_id = serializers.IntegerField(source='permission_group.id', read_only=True, allow_null=True)
    
    # Permissions for frontend convenience
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_superuser', 'project_name', 'project_id', 'date_joined', 'group_name', 'group_id', 'permissions', 'avatar']

    def get_permissions(self, obj):
        if obj.is_superuser:
            return {
                "dashboard": True, "issues": True, "users": True, "settings": True,
                "can_delete_issues": True,
                "can_create_project": True, "can_edit_project": True, "can_delete_project": True,
                "can_create_task": True, "can_edit_task": True, "can_delete_task": True,
                "can_view_user_projects": True,
                "backlog": True, "reports": True,
                "members": True, "can_manage_members": True,
                "chat": True,
                "docs": True, "can_create_doc": True, "can_edit_doc": True, "can_delete_doc": True,
                "can_manage_releases": True,
                "evaluations": True, "can_manage_evaluations": True,
                "performance": True, "notifications": True, "manage_permissions": True,
                "can_manage_sprints": True, "can_manage_epics": True,
            }

        group = obj.permission_group
        if not group:
            return {
                "dashboard": True, "issues": False, "users": False, "settings": False,
                "can_delete_issues": False,
                "can_create_project": False, "can_edit_project": False, "can_delete_project": False,
                "can_create_task": False, "can_edit_task": True, "can_delete_task": False,
                "can_view_user_projects": False,
                "backlog": True, "reports": True,
                "members": True, "can_manage_members": False,
                "chat": True,
                "docs": True, "can_create_doc": False, "can_edit_doc": False, "can_delete_doc": False,
                "can_manage_releases": False,
                "evaluations": False, "can_manage_evaluations": False,
                "performance": True, "notifications": True, "manage_permissions": False,
                "can_manage_sprints": False, "can_manage_epics": False,
            }

        return {
            "dashboard": group.can_view_dashboard,
            "issues": group.can_view_issues,
            "users": group.can_view_users,
            "settings": group.can_view_settings,
            "can_delete_issues": group.can_delete_issues,
            "can_create_project": group.can_create_project,
            "can_edit_project": group.can_edit_project,
            "can_delete_project": group.can_delete_project,
            "can_create_task": group.can_create_task,
            "can_edit_task": group.can_edit_task,
            "can_delete_task": group.can_delete_task,
            "can_view_user_projects": group.can_view_user_projects,
            "backlog": group.can_view_backlog,
            "reports": group.can_view_reports,
            "members": group.can_view_members,
            "can_manage_members": group.can_manage_members,
            "chat": group.can_view_chat,
            "docs": group.can_view_docs,
            "can_create_doc": group.can_create_doc,
            "can_edit_doc": group.can_edit_doc,
            "can_delete_doc": group.can_delete_doc,
            "can_manage_releases": group.can_manage_releases,
            "evaluations": group.can_view_evaluations,
            "can_manage_evaluations": group.can_manage_evaluations,
            "performance": group.can_view_performance,
            "notifications": group.can_view_notifications,
            "manage_permissions": group.can_manage_permissions,
            "can_manage_sprints": group.can_manage_sprints,
            "can_manage_epics": group.can_manage_epics,
        }

class IssueSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.username', read_only=True)

    class Meta:
        model = Issue
        fields = ['id', 'title', 'hash_id', 'project_name', 'project', 'status', 'first_seen', 'last_seen', 'counter', 'resolved_by_name']

class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['session_id', 'events_data', 'started_at']

class EventSerializer(serializers.ModelSerializer):
    # We can include related issue data if needed, or just the ID
    issue_title = serializers.CharField(source='issue.title', read_only=True)
    project_name = serializers.CharField(source='issue.project_name', read_only=True)
    status = serializers.CharField(source='issue.status', read_only=True)
    session_id = serializers.CharField(source='session.session_id', read_only=True, allow_null=True)
    
    # Custom field to indicate if we have a replay available
    has_session = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'issue', 'issue_title', 'project_name', 'status',
            'session', 'session_id', 'has_session',
            'timestamp', 'user_ident', 'url', 'traceback',
             # 'breadcrumbs', 'events_data' # These can be heavy, maybe exclude from list view?
        ]

    def get_has_session(self, obj):
        # Check if the event itself has data
        if obj.events_data:
            return True
        # Check if the related session has data
        if obj.session and obj.session.events_data:
            return True
        return False

class EventDetailSerializer(EventSerializer):
    class Meta(EventSerializer.Meta):
        fields = EventSerializer.Meta.fields + ['breadcrumbs', 'events_data']
