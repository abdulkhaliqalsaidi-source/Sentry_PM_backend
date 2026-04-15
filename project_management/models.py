from django.db import models
from django.conf import settings

class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class ProjectRole(models.Model):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('MEMBER', 'Member'),
        ('VIEWER', 'Viewer'),
    )
    project = models.ForeignKey(Project, related_name='roles', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='project_roles', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBER')
    
    class Meta:
        unique_together = ('project', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.role} in {self.project.name}"

class Sprint(models.Model):
    STATUS_CHOICES = (
        ('PLANNED', 'Planned'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
    )
    project = models.ForeignKey(Project, related_name='sprints', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    created_at = models.DateTimeField(auto_now_add=True)

    # ── Velocity fields (populated on complete) ──────────────────
    completed_points   = models.IntegerField(default=0, help_text="Story points completed in this sprint")
    committed_points   = models.IntegerField(default=0, help_text="Story points committed at sprint start")
    completed_tasks    = models.IntegerField(default=0, help_text="Number of tasks completed")
    total_tasks        = models.IntegerField(default=0, help_text="Total tasks in sprint")
    completed_at       = models.DateTimeField(null=True, blank=True, help_text="When the sprint was completed")

    def __str__(self):
        return f"{self.name} ({self.status})"

class Epic(models.Model):
    project = models.ForeignKey(Project, related_name='epics', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=7, default='#3B82F6') # Hex color
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Label(models.Model):
    project = models.ForeignKey(Project, related_name='labels', on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#3B82F6')

    def __str__(self):
        return self.name

class TaskStatus(models.Model):
    CATEGORY_CHOICES = (
        ('TO_DO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('PENDING', 'Pending'),
        ('IN_REVIEW', 'In Review'),
        ('DONE', 'Done'),
    )
    project = models.ForeignKey(Project, related_name='statuses', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#64748B')
    order = models.IntegerField(default=0)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='IN_PROGRESS')

    class Meta:
        ordering = ['order']
        unique_together = ('project', 'name')

    def __str__(self):
        return f"{self.name} ({self.project.name})"

class WorkflowTransition(models.Model):
    project = models.ForeignKey(Project, related_name='transitions', on_delete=models.CASCADE)
    from_status = models.ForeignKey(TaskStatus, related_name='outgoing_transitions', on_delete=models.CASCADE, null=True, blank=True)
    to_status = models.ForeignKey(TaskStatus, related_name='incoming_transitions', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('project', 'from_status', 'to_status')

    def __str__(self):
        from_name = self.from_status.name if self.from_status else "ANY"
        return f"{from_name} -> {self.to_status.name} in {self.project.name}"

class Task(models.Model):
    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    )

    ISSUE_TYPE_CHOICES = (
        ('TASK', 'Task'),
        ('STORY', 'Story'),
        ('BUG', 'Bug'),
    )

    project = models.ForeignKey(Project, related_name='tasks', on_delete=models.CASCADE)
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPE_CHOICES, default='TASK')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='assigned_tasks', on_delete=models.SET_NULL, null=True, blank=True)
    watchers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='watched_tasks', blank=True)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='reported_tasks', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.ForeignKey(TaskStatus, related_name='tasks', on_delete=models.PROTECT, null=True, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    story_points = models.IntegerField(default=0)
    environment = models.CharField(max_length=100, blank=True)
    labels = models.ManyToManyField(Label, related_name='tasks', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    time_spent = models.FloatField(default=0.0, help_text="Time spent in hours")
    time_estimate = models.FloatField(default=0.0, help_text="Estimated time in hours")

    # Optional field for linking with Sentry
    sentry_error_id = models.IntegerField(null=True, blank=True)
    
    # Sprint linkage (Null = Backlog)
    sprint = models.ForeignKey(Sprint, related_name='tasks', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Epic linkage
    epic = models.ForeignKey(Epic, related_name='tasks', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.title

class Comment(models.Model):
    task = models.ForeignKey(Task, related_name='comments', on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='task_comments', on_delete=models.CASCADE)
    content = models.TextField()  # Markdown supported
    parent = models.ForeignKey('self', related_name='replies', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.task}"

class WorkLog(models.Model):
    task = models.ForeignKey(Task, related_name='work_logs', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='work_logs', on_delete=models.CASCADE)
    hours = models.FloatField(help_text="Hours logged")
    description = models.CharField(max_length=255, blank=True)
    logged_at = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-logged_at']

    def __str__(self):
        return f"{self.user.username} logged {self.hours}h on {self.task}"

class Subtask(models.Model):
    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    )
    parent = models.ForeignKey(Task, related_name='subtasks', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='assigned_subtasks', on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.ForeignKey(TaskStatus, related_name='subtasks', on_delete=models.SET_NULL, null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Attachment(models.Model):
    task = models.ForeignKey(Task, related_name='attachments', on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='uploaded_attachments', on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='task_attachments/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Attachment {self.file.name} on {self.task}"

class IssueLink(models.Model):
    LINK_TYPES = (
        ('BLOCKS', 'Blocks'),
        ('IS_BLOCKED_BY', 'Is Blocked By'),
        ('RELATES_TO', 'Relates To'),
        ('DUPLICATES', 'Duplicates'),
        ('IS_DUPLICATED_BY', 'Is Duplicated By'),
    )
    from_task = models.ForeignKey(Task, related_name='outgoing_links', on_delete=models.CASCADE)
    to_task = models.ForeignKey(Task, related_name='incoming_links', on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=LINK_TYPES, default='RELATES_TO')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_task', 'to_task', 'type')

    def __str__(self):
        return f"{self.from_task.id} {self.type} {self.to_task.id}"

class Notification(models.Model):
    TYPES = (
        ('ASSIGNMENT', 'Assignment'),
        ('STATUS_CHANGE', 'Status Change'),
        ('COMMENT', 'Comment'),
        ('MENTION', 'Mention'),
        ('SYSTEM', 'System'),
    )
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications', on_delete=models.CASCADE)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications_created', on_delete=models.CASCADE)
    verb = models.CharField(max_length=100) # e.g., "assigned you to", "changed status of"
    type = models.CharField(max_length=20, choices=TYPES, default='SYSTEM')
    task = models.ForeignKey(Task, related_name='notifications', on_delete=models.CASCADE, null=True, blank=True)
    project = models.ForeignKey('Project', null=True, blank=True, on_delete=models.SET_NULL)
    actor_count = models.IntegerField(default=1)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.actor} {self.verb} {self.task} -> {self.recipient}"
class ProjectMessage(models.Model):
    project = models.ForeignKey(Project, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='project_messages', on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    is_deleted = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} in {self.project.name} at {self.created_at}"

class MessageReaction(models.Model):
    message = models.ForeignKey(ProjectMessage, related_name='reactions', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user', 'emoji')

    def __str__(self):
        return f"{self.user.username} reacted {self.emoji} on message {self.message_id}"


class PinnedMessage(models.Model):
    project = models.ForeignKey(Project, related_name='pinned_messages', on_delete=models.CASCADE)
    message = models.ForeignKey(ProjectMessage, on_delete=models.CASCADE)
    pinned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    pinned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'message')

    def __str__(self):
        return f"Pinned message {self.message_id} in {self.project.name}"


class UnreadCount(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    count = models.IntegerField(default=0)
    last_read_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'user')

    def __str__(self):
        return f"{self.user.username} unread {self.count} in {self.project.name}"


class ChatAttachment(models.Model):
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='chat_attachments/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment {self.file.name} by {self.uploaded_by.username}"


class DocTag(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='doc_tags')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#3B82F6')

    class Meta:
        unique_together = ('project', 'name')

    def __str__(self):
        return self.name


class Documentation(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents', verbose_name="المشروع المرتبط")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name="التوثيق الأب")
    title = models.CharField(max_length=255, verbose_name="عنوان التوثيق")
    content = models.TextField(verbose_name="المحتوى (Markdown)")
    is_published = models.BooleanField(default=True, verbose_name="منشور")
    order = models.IntegerField(default=0, verbose_name="الترتيب")
    tags = models.ManyToManyField(DocTag, related_name='documents', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_docs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.title} - {self.project.name}"

class DocumentRevision(models.Model):
    document = models.ForeignKey(Documentation, on_delete=models.CASCADE, related_name='revisions')
    content = models.TextField(verbose_name="المحتوى في هذه النسخة")
    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="المُعدِّل")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التعديل")

    class Meta:
        ordering = ['-created_at']

class DocComment(models.Model):
    document = models.ForeignKey(Documentation, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username} on {self.document.title}"


class APIEndpoint(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='api_endpoints', verbose_name="المشروع")
    app_name = models.CharField(max_length=255, verbose_name="التطبيق (App)")
    path = models.CharField(max_length=500, verbose_name="المسار (Path)")
    method = models.CharField(max_length=10, verbose_name="النوع (Method)")
    description = models.TextField(blank=True, null=True, verbose_name="الوصف")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات المطورين")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['app_name', 'path', 'method']

    def __str__(self):
        return f"[{self.method}] {self.path} ({self.app_name})"


# ─────────────────────────────────────────────────────────────────────────────
# Developer Evaluation System
# ─────────────────────────────────────────────────────────────────────────────

class EvaluationPeriod(models.Model):
    """A named window of time used for evaluations (e.g. 'Q1 2025')."""
    project = models.ForeignKey(
        Project, related_name='evaluation_periods',
        on_delete=models.CASCADE, null=True, blank=True,
        help_text="Leave blank for a global (cross-project) period."
    )
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name


class KPI(models.Model):
    """A single performance indicator with a weight."""
    TYPE_CHOICES = (
        ('AUTOMATED', 'Automated'),   # calculated from task data
        ('MANUAL',    'Manual'),       # entered by a manager
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='AUTOMATED')
    weight = models.FloatField(
        default=1.0,
        help_text="Relative weight used in the final score calculation."
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.type})"


class UserEvaluation(models.Model):
    """Aggregated evaluation record for one user in one period."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='evaluations',
        on_delete=models.CASCADE
    )
    period = models.ForeignKey(
        EvaluationPeriod, related_name='evaluations',
        on_delete=models.CASCADE
    )
    # 0-100 composite score (auto-computed)
    score = models.FloatField(default=0.0)
    # Gamification points accumulated during this period
    points = models.IntegerField(default=0)
    # Free-text summary from the manager
    manager_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'period')
        ordering = ['-period__start_date']

    def __str__(self):
        return f"{self.user.username} – {self.period.name} ({self.score:.1f})"


class EvaluationDetail(models.Model):
    """Score for a single KPI within a UserEvaluation."""
    evaluation = models.ForeignKey(
        UserEvaluation, related_name='details',
        on_delete=models.CASCADE
    )
    kpi = models.ForeignKey(
        KPI, related_name='details',
        on_delete=models.CASCADE
    )
    # 0-100 raw score for this specific KPI
    score = models.FloatField(default=0.0)
    # Optional raw value (e.g. "12 tasks closed", "3.4 days avg lead time")
    raw_value = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('evaluation', 'kpi')

    def __str__(self):
        return f"{self.kpi.name}: {self.score} for {self.evaluation}"


# Signal for Notifications
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@receiver(post_save, sender=Notification)
def broadcast_notification(sender, instance, created, **kwargs):
    if created:
        from .serializers import NotificationSerializer
        channel_layer = get_channel_layer()
        group_name = f'user_notifications_{instance.recipient.username}'
        
        # Serialize the notification to send to frontend
        serializer = NotificationSerializer(instance)
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'notification_message',
                'data': serializer.data
            }
        )

# ─────────────────────────────────────────────────────────────────────────────
# Custom Fields System
# ─────────────────────────────────────────────────────────────────────────────

class CustomField(models.Model):
    FIELD_TYPES = (
        ('TEXT', 'Text'),
        ('NUMBER', 'Number'),
        ('DATE', 'Date'),
        ('USER', 'User'),
        ('CHOICE', 'Choice'),
    )
    project = models.ForeignKey(Project, related_name='custom_fields', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='TEXT')
    required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.project.name})"

class CustomFieldOption(models.Model):
    custom_field = models.ForeignKey(CustomField, related_name='options', on_delete=models.CASCADE)
    value = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.custom_field.name} - {self.value}"

class TaskCustomFieldValue(models.Model):
    task = models.ForeignKey(Task, related_name='custom_field_values', on_delete=models.CASCADE)
    custom_field = models.ForeignKey(CustomField, related_name='values', on_delete=models.CASCADE)
    value_text = models.TextField(blank=True, null=True)
    value_number = models.FloatField(blank=True, null=True)
    value_date = models.DateTimeField(blank=True, null=True)
    value_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('task', 'custom_field')

    def __str__(self):
        return f"{self.custom_field.name} for {self.task.title}"

# ─────────────────────────────────────────────────────────────────────────────
# Automation Rules Engine
# ─────────────────────────────────────────────────────────────────────────────

class AutomationRule(models.Model):
    project = models.ForeignKey(Project, related_name='automation_rules', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.project.name})"

class AutomationTrigger(models.Model):
    TRIGGER_TYPES = (
        ('TASK_CREATED', 'Task Created'),
        ('TASK_UPDATED', 'Task Updated'),
        ('STATUS_CHANGED', 'Status Changed'),
        ('ASSIGNEE_CHANGED', 'Assignee Changed'),
    )
    rule = models.ForeignKey(AutomationRule, related_name='triggers', on_delete=models.CASCADE)
    trigger_type = models.CharField(max_length=50, choices=TRIGGER_TYPES)

    def __str__(self):
        return f"{self.trigger_type} for {self.rule.name}"

class AutomationCondition(models.Model):
    OPERATORS = (
        ('EQUALS', 'Equals'),
        ('NOT_EQUALS', 'Not Equals'),
        ('CONTAINS', 'Contains'),
        ('GREATER_THAN', 'Greater Than'),
        ('LESS_THAN', 'Less Than'),
    )
    rule = models.ForeignKey(AutomationRule, related_name='conditions', on_delete=models.CASCADE)
    field = models.CharField(max_length=100)  # e.g., 'status.name', 'priority', 'custom_field_id'
    operator = models.CharField(max_length=20, choices=OPERATORS)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.field} {self.operator} {self.value}"

class AutomationAction(models.Model):
    ACTION_TYPES = (
        ('SET_STATUS', 'Set Status'),
        ('ASSIGN_USER', 'Assign User'),
        ('ADD_LABEL', 'Add Label'),
        ('ADD_COMMENT', 'Add Comment'),
        ('SEND_NOTIFICATION', 'Send Notification'),
    )
    rule = models.ForeignKey(AutomationRule, related_name='actions', on_delete=models.CASCADE)
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    parameters = models.JSONField(default=dict)  # e.g., {"status_id": 12, "user_id": 5}

    def __str__(self):
        return f"{self.action_type} for {self.rule.name}"

# ─────────────────────────────────────────────────────────────────────────────
# Release / Version Management
# ─────────────────────────────────────────────────────────────────────────────

class Version(models.Model):
    STATUS_CHOICES = (
        ('UNRELEASED', 'Unreleased'),
        ('RELEASED', 'Released'),
        ('ARCHIVED', 'Archived'),
    )
    project = models.ForeignKey(Project, related_name='versions', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNRELEASED')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.project.name})"

class ReleaseNote(models.Model):
    version = models.OneToOneField(Version, related_name='release_note', on_delete=models.CASCADE)
    description = models.TextField()
    published_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notes for {self.version.name}"

class TaskVersion(models.Model):
    RELATION_TYPES = (
        ('FIXED_IN', 'Fixed In'),
        ('AFFECTS', 'Affects'),
        ('IMPLEMENTED_IN', 'Implemented In'),
    )
    task = models.ForeignKey(Task, related_name='version_relations', on_delete=models.CASCADE)
    version = models.ForeignKey(Version, related_name='task_relations', on_delete=models.CASCADE)
    relation_type = models.CharField(max_length=20, choices=RELATION_TYPES, default='FIXED_IN')

    class Meta:
        unique_together = ('task', 'version', 'relation_type')

    def __str__(self):
        return f"{self.task.title} {self.relation_type} {self.version.name}"

# ─────────────────────────────────────────────────────────────────────────────
# Plugin Architecture
# ─────────────────────────────────────────────────────────────────────────────

class PluginModel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    version = models.CharField(max_length=20)
    description = models.TextField(blank=True, default='')
    enabled = models.BooleanField(default=False)
    entry_point = models.CharField(max_length=255, help_text="Module path, e.g., 'plugins.myplugin'")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} v{self.version} ({'Enabled' if self.enabled else 'Disabled'})"
