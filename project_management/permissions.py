"""
Custom DRF permission classes based on PermissionGroup.
Usage:
    from project_management.permissions import HasPerm
    permission_classes = [HasPerm('can_view_docs')]
"""
from rest_framework.permissions import BasePermission


def _get_group(user):
    """Return the user's PermissionGroup or None."""
    if not user or not user.is_authenticated:
        return None
    return getattr(user, 'permission_group', None)


class HasPerm(BasePermission):
    """
    Generic permission class. Pass the model field name as perm_field.
    Superusers always pass. Users without a group are denied by default.
    """
    def __init__(self, perm_field: str, allow_no_group: bool = False):
        self.perm_field = perm_field
        self.allow_no_group = allow_no_group

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        group = _get_group(request.user)
        if group is None:
            return self.allow_no_group
        return bool(getattr(group, self.perm_field, False))


# ── Pre-built permission classes ──────────────────────────────────────────────

class CanViewDashboard(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_view_dashboard)

class CanViewIssues(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_view_issues)

class CanDeleteIssues(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_delete_issues)

class CanViewUsers(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_view_users)

class CanViewSettings(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_view_settings)

class CanCreateProject(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_create_project)

class CanCreateTask(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_create_task)

class CanViewBacklog(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_view_backlog)

class CanViewReports(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_view_reports)

class CanViewMembers(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_view_members)

class CanViewChat(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_view_chat)

class CanViewDocs(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_view_docs)

class CanViewEvaluations(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_view_evaluations)

class CanViewPerformance(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_view_performance)

class CanManagePermissions(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_manage_permissions)


class CanEditProject(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_edit_project)

class CanDeleteProject(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_delete_project)

class CanEditTask(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_edit_task)

class CanDeleteTask(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_delete_task)

class CanManageMembers(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_manage_members)

class CanCreateDoc(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_create_doc)

class CanEditDoc(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_edit_doc)

class CanDeleteDoc(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_delete_doc)

class CanManageReleases(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_manage_releases)

class CanManageEvaluations(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_manage_evaluations)

class CanManageSprints(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_manage_sprints)

class CanManageEpics(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        g = _get_group(request.user)
        return bool(g and g.can_manage_epics)


# ── Read/Write split helper ───────────────────────────────────────────────────

class ReadOrHasPerm(BasePermission):
    """
    Allow GET/HEAD/OPTIONS freely (if authenticated),
    but require perm_field for write operations.
    """
    def __init__(self, perm_field: str):
        self.perm_field = perm_field

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        g = _get_group(request.user)
        return bool(g and getattr(g, self.perm_field, False))
