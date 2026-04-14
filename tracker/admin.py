from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Issue, Event, Session, Project, User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'primary_project', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('primary_project',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('primary_project',)}),
    )

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'api_key', 'created_at')
    search_fields = ('name', 'api_key')
    readonly_fields = ('api_key', 'created_at')

@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'counter', 'last_seen')
    list_filter = ('status', 'project')
    search_fields = ('title', 'hash_id')
    readonly_fields = ('hash_id', 'first_seen', 'last_seen')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('issue', 'user_ident', 'timestamp', 'has_session')
    list_filter = ('timestamp',)
    search_fields = ('user_ident', 'url')
    
    def has_session(self, obj):
        return obj.session is not None
    has_session.boolean = True

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'started_at', 'event_count')
    search_fields = ('session_id',)
    
    def event_count(self, obj):
        return len(obj.events_data)
