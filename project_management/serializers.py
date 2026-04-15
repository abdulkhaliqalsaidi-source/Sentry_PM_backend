from rest_framework import serializers
from django.utils import timezone
from .models import Project, Task, Comment, Subtask, Sprint, Epic, Label, ProjectRole, Attachment, IssueLink, TaskStatus, WorkflowTransition, Documentation, DocumentRevision, APIEndpoint, EvaluationPeriod, KPI, UserEvaluation, EvaluationDetail, WorkLog

class APIEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIEndpoint
        fields = '__all__'

class SprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sprint
        fields = '__all__'

class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.username')
    author_avatar = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'task', 'author', 'author_name', 'author_avatar', 'content', 'parent', 'replies', 'created_at', 'updated_at']
        read_only_fields = ['author']

    def get_author_avatar(self, obj):
        if obj.author and obj.author.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.author.avatar.url)
            return obj.author.avatar.url
        return None

    def get_replies(self, obj):
        # Only return replies for top-level comments (parent=None)
        if obj.parent is not None:
            return []
        qs = obj.replies.select_related('author').order_by('created_at')
        return CommentSerializer(qs, many=True, context=self.context).data


class WorkLogSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = WorkLog
        fields = ['id', 'task', 'user', 'username', 'hours', 'description', 'logged_at', 'created_at']
        read_only_fields = ['user']


class SubtaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.ReadOnlyField(source='assigned_to.username')
    status_details = serializers.SerializerMethodField()

    class Meta:
        model = Subtask
        fields = ['id', 'parent', 'title', 'description', 'assigned_to', 'assigned_to_name',
                  'priority', 'status', 'status_details', 'is_completed', 'due_date', 'created_at']

    def get_status_details(self, obj):
        if obj.status:
            return {'id': obj.status.id, 'name': obj.status.name, 'color': obj.status.color, 'category': obj.status.category}
        return None

class ProjectSerializer(serializers.ModelSerializer):
    total_tasks = serializers.SerializerMethodField()
    completed_tasks = serializers.SerializerMethodField()
    in_progress_tasks = serializers.SerializerMethodField()
    health = serializers.SerializerMethodField()
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Project
        fields = '__all__'

    def get_total_tasks(self, obj):
        return obj.tasks.count()

    def get_completed_tasks(self, obj):
        return obj.tasks.filter(status__category='DONE').count()

    def get_in_progress_tasks(self, obj):
        return obj.tasks.filter(status__category__in=['IN_PROGRESS', 'PENDING', 'IN_REVIEW']).count()

    def get_health(self, obj):
        total = obj.tasks.count()
        if total == 0:
            return 100
        done = obj.tasks.filter(status__category='DONE').count()
        overdue = obj.tasks.filter(
            end_date__isnull=False,
            end_date__lt=timezone.now()
        ).exclude(status__category='DONE').count()
        completion_ratio = (done / total) * 100
        overdue_penalty = min((overdue / total) * 30, 30)
        return round(max(completion_ratio - overdue_penalty, 0))

class ProjectRoleSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    email = serializers.ReadOnlyField(source='user.email')

    class Meta:
        model = ProjectRole
        fields = ['id', 'project', 'user', 'role', 'username', 'email']

class EpicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Epic
        fields = '__all__'

class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = '__all__'

class TaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStatus
        fields = '__all__'

class WorkflowTransitionSerializer(serializers.ModelSerializer):
    from_status_name = serializers.ReadOnlyField(source='from_status.name')
    to_status_name = serializers.ReadOnlyField(source='to_status.name')

    class Meta:
        model = WorkflowTransition
        fields = ['id', 'project', 'from_status', 'to_status', 'from_status_name', 'to_status_name']

class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.ReadOnlyField(source='uploaded_by.username')
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'task', 'uploaded_by', 'uploaded_by_name', 'file', 'file_name', 'created_at']
        read_only_fields = ['uploaded_by']

    def get_file_name(self, obj):
        import os
        return os.path.basename(obj.file.name)

class IssueLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueLink
        fields = '__all__'

from .models import (
    CustomField, CustomFieldOption, TaskCustomFieldValue,
    AutomationRule, AutomationTrigger, AutomationCondition, AutomationAction,
    Version, ReleaseNote, TaskVersion, PluginModel
)

# ─── Custom Fields Serializers ───────────────────────────────────────────────

class CustomFieldOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomFieldOption
        fields = '__all__'

class CustomFieldSerializer(serializers.ModelSerializer):
    options = CustomFieldOptionSerializer(many=True, read_only=True)
    class Meta:
        model = CustomField
        fields = '__all__'

class TaskCustomFieldValueSerializer(serializers.ModelSerializer):
    field_name = serializers.ReadOnlyField(source='custom_field.name')
    field_type = serializers.ReadOnlyField(source='custom_field.field_type')
    
    class Meta:
        model = TaskCustomFieldValue
        fields = ['id', 'task', 'custom_field', 'field_name', 'field_type', 
                  'value_text', 'value_number', 'value_date', 'value_user']

# ─── Automation Rule Serializers ─────────────────────────────────────────────

class AutomationTriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationTrigger
        fields = '__all__'

class AutomationConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationCondition
        fields = '__all__'

class AutomationActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationAction
        fields = '__all__'

class AutomationRuleSerializer(serializers.ModelSerializer):
    triggers = AutomationTriggerSerializer(many=True, read_only=True)
    conditions = AutomationConditionSerializer(many=True, read_only=True)
    actions = AutomationActionSerializer(many=True, read_only=True)

    class Meta:
        model = AutomationRule
        fields = '__all__'

# ─── Version & Release Serializers ───────────────────────────────────────────

class ReleaseNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReleaseNote
        fields = '__all__'

class VersionSerializer(serializers.ModelSerializer):
    release_note = ReleaseNoteSerializer(read_only=True)
    class Meta:
        model = Version
        fields = '__all__'

class TaskVersionSerializer(serializers.ModelSerializer):
    version_name = serializers.ReadOnlyField(source='version.name')
    class Meta:
        model = TaskVersion
        fields = ['id', 'task', 'version', 'version_name', 'relation_type']

# ─── Plugin Serializer ───────────────────────────────────────────

class PluginModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PluginModel
        fields = '__all__'

class TaskSerializer(serializers.ModelSerializer):
    assignee_name = serializers.SerializerMethodField()
    watcher_names = serializers.SerializerMethodField()
    subtasks = SubtaskSerializer(many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()
    epic_details = EpicSerializer(source='epic', read_only=True)
    labels_details = LabelSerializer(source='labels', many=True, read_only=True)
    reporter_name = serializers.ReadOnlyField(source='reporter.username')
    status_details = TaskStatusSerializer(source='status', read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    outgoing_links = IssueLinkSerializer(many=True, read_only=True)
    incoming_links = IssueLinkSerializer(many=True, read_only=True)
    custom_field_values = TaskCustomFieldValueSerializer(many=True, read_only=True)
    version_relations = TaskVersionSerializer(many=True, read_only=True)
    work_logs = WorkLogSerializer(many=True, read_only=True)
    total_logged = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = '__all__'
        extra_kwargs = {
            'status': {'required': False, 'allow_null': True},
            'reporter': {'required': False, 'allow_null': True},
        }

    def get_assignee_name(self, obj):
        return obj.assigned_to.username if obj.assigned_to else None

    def get_watcher_names(self, obj):
        return list(obj.watchers.values_list('username', flat=True))

    def get_comments_count(self, obj):
        if hasattr(obj, 'comments_count_annotated'):
            return obj.comments_count_annotated
        return obj.comments.count()

    def get_total_logged(self, obj):
        return sum(log.hours for log in obj.work_logs.all())

class DocumentRevisionSerializer(serializers.ModelSerializer):
    editor_name = serializers.CharField(source='edited_by.username', read_only=True)
    
    class Meta:
        model = DocumentRevision
        fields = ['id', 'content', 'editor_name', 'created_at']

from .models import DocTag

class DocTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocTag
        fields = ['id', 'project', 'name', 'color']

class DocumentationSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent_title = serializers.ReadOnlyField(source='parent.title')
    tags_details = DocTagSerializer(source='tags', many=True, read_only=True)
    
    class Meta:
        model = Documentation
        fields = ['id', 'project', 'parent', 'parent_title', 'title', 'content', 'is_published', 'order', 'tags', 'tags_details', 'created_by', 'created_at', 'updated_at', 'children']

    def get_children(self, obj):
        children = obj.children.all().order_by('order', 'created_at')
        return DocumentationSerializer(children, many=True).data if children.exists() else []

from .models import Notification, ProjectMessage, DocComment

class DocCommentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = DocComment
        fields = ['id', 'document', 'author', 'content', 'created_at', 'updated_at']
        read_only_fields = ['author', 'created_at', 'updated_at']



class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.ReadOnlyField(source='actor.username')
    actor_username = serializers.ReadOnlyField(source='actor.username')
    task_title = serializers.ReadOnlyField(source='task.title')
    project_id = serializers.ReadOnlyField(source='task.project_id')
    task_details = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = '__all__'

    def get_task_details(self, obj):
        if obj.task:
            return {
                'id': obj.task.id,
                'title': obj.task.title,
                'project_id': obj.task.project_id
            }
        return None
class SimpleProjectMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source='sender.username')
    class Meta:
        model = ProjectMessage
        fields = ['id', 'sender_username', 'content', 'created_at', 'is_deleted', 'is_edited']

class ProjectMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source='sender.username')
    reply_to_details = SimpleProjectMessageSerializer(source='reply_to', read_only=True)

    class Meta:
        model = ProjectMessage
        fields = ['id', 'project', 'sender', 'sender_username', 'content', 'reply_to', 'reply_to_details', 'is_deleted', 'is_edited', 'attachment', 'created_at']
        read_only_fields = ['sender', 'created_at']


# ─── Evaluation Serializers ───────────────────────────────────────────────────

class EvaluationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationPeriod
        fields = '__all__'


class KPISerializer(serializers.ModelSerializer):
    class Meta:
        model = KPI
        fields = '__all__'


class EvaluationDetailSerializer(serializers.ModelSerializer):
    kpi_name = serializers.ReadOnlyField(source='kpi.name')
    kpi_type = serializers.ReadOnlyField(source='kpi.type')
    kpi_weight = serializers.ReadOnlyField(source='kpi.weight')

    class Meta:
        model = EvaluationDetail
        fields = ['id', 'evaluation', 'kpi', 'kpi_name', 'kpi_type', 'kpi_weight',
                  'score', 'raw_value', 'notes', 'created_at']


class UserEvaluationSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    period_name = serializers.ReadOnlyField(source='period.name')
    details = EvaluationDetailSerializer(many=True, read_only=True)

    class Meta:
        model = UserEvaluation
        fields = ['id', 'user', 'username', 'period', 'period_name',
                  'score', 'points', 'manager_notes', 'details',
                  'created_at', 'updated_at']

