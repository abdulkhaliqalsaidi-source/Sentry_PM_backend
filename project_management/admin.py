from django.contrib import admin

from .models import Project, Task, TaskStatus, Sprint

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at')
    search_fields = ('name', 'description')

@admin.register(TaskStatus)
class TaskStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'category', 'order', 'color')
    list_filter = ('project', 'category')
    ordering = ('project', 'order')

@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'status', 'start_date', 'end_date')
    list_filter = ('project', 'status')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'priority', 'get_assignee', 'created_at')
    list_filter = ('status', 'priority', 'project')
    search_fields = ('title', 'description', 'sentry_error_id')
    filter_horizontal = ('watchers', 'labels')

    def get_assignee(self, obj):
        return obj.assigned_to.username if obj.assigned_to else 'Unassigned'
    get_assignee.short_description = 'Assignee'
