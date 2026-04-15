from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Project, Task, Comment, Subtask, Sprint, Epic, Label, ProjectRole, Attachment, IssueLink, TaskStatus, WorkflowTransition, Notification, ProjectMessage, APIEndpoint, EvaluationPeriod, KPI, UserEvaluation, EvaluationDetail, WorkLog, Documentation, DocumentRevision, DocTag
from .serializers import ProjectSerializer, TaskSerializer, CommentSerializer, SubtaskSerializer, SprintSerializer, EpicSerializer, LabelSerializer, ProjectRoleSerializer, AttachmentSerializer, IssueLinkSerializer, TaskStatusSerializer, WorkflowTransitionSerializer, NotificationSerializer, ProjectMessageSerializer, DocumentationSerializer, DocumentRevisionSerializer, APIEndpointSerializer, EvaluationPeriodSerializer, KPISerializer, UserEvaluationSerializer, EvaluationDetailSerializer, WorkLogSerializer
from .permissions import (
    CanViewDashboard, CanViewIssues, CanDeleteIssues, CanViewUsers,
    CanViewSettings, CanCreateProject, CanCreateTask, CanViewBacklog,
    CanViewReports, CanViewMembers, CanViewChat, CanViewDocs,
    CanViewEvaluations, CanViewPerformance, CanManagePermissions,
    ReadOrHasPerm, HasPerm,
    CanEditProject, CanDeleteProject, CanEditTask, CanDeleteTask,
    CanManageMembers, CanCreateDoc, CanEditDoc, CanDeleteDoc,
    CanManageReleases, CanManageEvaluations, CanManageSprints, CanManageEpics
)
from .utils.api_extractor import analyze_django_zip
import tempfile
import os
import sys
import uuid
from django.conf import settings


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_doc_image(request):
    """Upload an image for the documentation editor and return its public URL."""
    image = request.FILES.get('image')
    if not image:
        return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate it is actually an image
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
    if image.content_type not in allowed_types:
        return Response({'error': 'Invalid file type'}, status=status.HTTP_400_BAD_REQUEST)

    # Generate a unique filename to avoid collisions
    ext = os.path.splitext(image.name)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join('doc_images', filename)

    # Save the file
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile

    path = default_storage.save(save_path, ContentFile(image.read()))
    url = request.build_absolute_uri(settings.MEDIA_URL + path)
    return Response({'url': url})




class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Notification.objects.all()
        user = self.request.user
        
        # Filter by authenticated user (non-superusers only see their own)
        if user and user.is_authenticated and not user.is_superuser:
            queryset = queryset.filter(recipient=user)
        
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            if is_read.lower() == 'true':
                queryset = queryset.filter(is_read=True)
            elif is_read.lower() == 'false':
                queryset = queryset.filter(is_read=False)
                
        type_filter = self.request.query_params.get('type')
        if type_filter:
            queryset = queryset.filter(type=type_filter)

        return queryset

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        queryset = self.get_queryset()
        queryset.update(is_read=True)
        return Response({'status': 'all notifications marked as read'})

    @action(detail=False, methods=['delete'], url_path='delete-all')
    def delete_all(self, request):
        queryset = self.get_queryset()
        count, _ = queryset.delete()
        return Response({'status': f'{count} notifications deleted'})

class SprintViewSet(viewsets.ModelViewSet):
    queryset = Sprint.objects.all()
    serializer_class = SprintSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [CanManageSprints()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Sprint.objects.all()
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        from django.db.models import Sum
        sprint = self.get_object()
        # Snapshot committed points at start
        sprint.committed_points = sprint.tasks.aggregate(s=Sum('story_points'))['s'] or 0
        sprint.total_tasks = sprint.tasks.count()
        sprint.status = 'ACTIVE'
        sprint.save()
        return Response({'status': 'sprint started'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        from django.utils import timezone
        from django.db.models import Sum

        sprint = self.get_object()
        move_to_sprint_id = request.data.get('move_to')

        all_tasks   = sprint.tasks.all()
        done_tasks  = all_tasks.filter(status__category='DONE')
        incomplete  = all_tasks.exclude(status__category='DONE')

        # ── Calculate velocity before moving tasks ────────────────
        sprint.committed_points = all_tasks.aggregate(s=Sum('story_points'))['s'] or 0
        sprint.completed_points = done_tasks.aggregate(s=Sum('story_points'))['s'] or 0
        sprint.total_tasks      = all_tasks.count()
        sprint.completed_tasks  = done_tasks.count()
        sprint.completed_at     = timezone.now()

        # ── Move incomplete tasks ─────────────────────────────────
        target_sprint = None
        if move_to_sprint_id:
            try:
                target_sprint = Sprint.objects.get(id=move_to_sprint_id, project=sprint.project)
            except Sprint.DoesNotExist:
                pass

        moved = incomplete.update(sprint=target_sprint)

        sprint.status = 'COMPLETED'
        sprint.save()

        return Response({
            'status': 'sprint completed',
            'moved_tasks': moved,
            'velocity': {
                'completed_points': sprint.completed_points,
                'committed_points': sprint.committed_points,
                'completed_tasks':  sprint.completed_tasks,
                'total_tasks':      sprint.total_tasks,
            }
        })

class EpicViewSet(viewsets.ModelViewSet):
    queryset = Epic.objects.all()
    serializer_class = EpicSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [CanManageEpics()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Epic.objects.all()
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset


class LabelViewSet(viewsets.ModelViewSet):
    queryset = Label.objects.all()
    serializer_class = LabelSerializer

    def get_queryset(self):
        qs = Label.objects.all()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        if user:
            serializer.save(uploaded_by=user)
        else:
            serializer.save()

    def get_queryset(self):
        queryset = Attachment.objects.all()
        task_id = self.request.query_params.get('task')
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        return queryset

class IssueLinkViewSet(viewsets.ModelViewSet):
    queryset = IssueLink.objects.all()
    serializer_class = IssueLinkSerializer

    def get_queryset(self):
        queryset = IssueLink.objects.all()
        from_task = self.request.query_params.get('from_task')
        to_task = self.request.query_params.get('to_task')
        task = self.request.query_params.get('task')

        if from_task:
            queryset = queryset.filter(from_task_id=from_task)
        if to_task:
            queryset = queryset.filter(to_task_id=to_task)
        if task:
            from django.db.models import Q
            queryset = queryset.filter(Q(from_task_id=task) | Q(to_task_id=task))
        return queryset

class TaskStatusViewSet(viewsets.ModelViewSet):
    queryset = TaskStatus.objects.all()
    serializer_class = TaskStatusSerializer

    def get_queryset(self):
        queryset = TaskStatus.objects.all()
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset

class WorkflowTransitionViewSet(viewsets.ModelViewSet):
    queryset = WorkflowTransition.objects.all()
    serializer_class = WorkflowTransitionSerializer

    def get_queryset(self):
        queryset = WorkflowTransition.objects.all()
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset

class ProjectRoleViewSet(viewsets.ModelViewSet):
    queryset = ProjectRole.objects.all()
    serializer_class = ProjectRoleSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [CanManageMembers()]
        return [CanViewMembers()]

    def get_queryset(self):
        queryset = ProjectRole.objects.all()
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
            
        username = self.request.query_params.get('username')
        if username:
            queryset = queryset.filter(user__username=username)
            
        return queryset

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':
            return [CanCreateProject()]
        if self.action in ('update', 'partial_update'):
            return [CanEditProject()]
        if self.action == 'destroy':
            return [CanDeleteProject()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return Project.objects.none()
        
        if user.is_superuser:
            return Project.objects.all()
        
        from django.db.models import Q
        query = Q(owner=user) | Q(roles__user=user)
        if hasattr(user, 'primary_project') and user.primary_project:
            query = query | Q(name=user.primary_project.name)
        
        return Project.objects.filter(query).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

from rest_framework import filters

class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':
            return [CanCreateTask()]
        if self.action in ('update', 'partial_update'):
            return [CanEditTask()]
        if self.action == 'destroy':
            return [CanDeleteTask()]
        return [IsAuthenticated()]

    queryset = Task.objects.select_related(
        'assigned_to', 'reporter', 'epic', 'status', 'project'
    ).prefetch_related(
        'watchers', 'subtasks', 'labels', 'attachments', 'attachments__uploaded_by',
        'outgoing_links', 'incoming_links', 'work_logs', 'work_logs__user'
    ).all()
    serializer_class = TaskSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description', 'epic__name']
    
    def get_queryset(self):
        from tracker.models import User
        from django.db.models import Count
        queryset = self.queryset.annotate(
            comments_count_annotated=Count('comments', distinct=True)
        )
        
        # Filter by Sprint
        sprint_id = self.request.query_params.get('sprint')
        if sprint_id == 'null':
            queryset = queryset.filter(sprint__isnull=True)
        elif sprint_id:
            queryset = queryset.filter(sprint_id=sprint_id)

        # Archiving logic (Jira-style)
        # By default, hide DONE tasks from the backlog and active boards.
        # Front-end can pass archived=true to see them.
        archived = self.request.query_params.get('archived', 'false').lower()
        if archived == 'false':
            # Only apply auto-archiving if NOT looking for a specific sprint
            if not sprint_id or sprint_id == 'null':
                # Hide tasks that belong to a COMPLETED sprint
                queryset = queryset.exclude(sprint__status='COMPLETED')
                # If sprint is null (Backlog/Kanban), hide tasks that are DONE
                queryset = queryset.exclude(status__category='DONE')

        # Filter by Status
        status_id = self.request.query_params.get('status')
        if status_id:
            queryset = queryset.filter(status_id=status_id)
        
        # Filter by explicit Query Param (always respected)
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # Filter by Priority
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
            
        # Filter by Assignee
        assigned_to = self.request.query_params.get('assigned_to')
        if assigned_to:
            if assigned_to == 'unassigned':
                queryset = queryset.filter(assigned_to__isnull=True)
            else:
                queryset = queryset.filter(assigned_to__id=assigned_to)
        
        # Filter by Epic
        epic_id = self.request.query_params.get('epic')
        if epic_id:
            queryset = queryset.filter(epic_id=epic_id)
            
        # User Context Filtering — use authenticated user from JWT
        user = self.request.user
        if user and user.is_authenticated and not user.is_superuser:
            from django.db.models import Q
            query = Q(project__owner=user) | Q(project__roles__user=user)
            if hasattr(user, 'primary_project') and user.primary_project:
                query = query | Q(project__name=user.primary_project.name)
            queryset = queryset.filter(query).distinct()

        # Filter by Date Range (created_at)
        created_after = self.request.query_params.get('created_after')
        if created_after:
            queryset = queryset.filter(created_at__date__gte=created_after)

        created_before = self.request.query_params.get('created_before')
        if created_before:
            queryset = queryset.filter(created_at__date__lte=created_before)

        return queryset


    def perform_create(self, serializer):
        # Auto-assign first status if not provided or null
        project = serializer.validated_data.get('project')
        status = serializer.validated_data.get('status')
        
        if project and not status:
            from .models import TaskStatus
            default_status = TaskStatus.objects.filter(
                project=project
            ).order_by('order', 'id').first()
            if default_status:
                serializer.validated_data['status'] = default_status

        task = serializer.save()
        # Fire automation: TASK_CREATED
        try:
            from .automation_engine import AutomationEngine
            AutomationEngine.process_event('TASK_CREATED', task.project_id, task=task)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Automation error on create: {e}")
        # Fire plugin event
        try:
            from plugins import fire
            fire('on_task_created', task=task)
        except Exception:
            pass

    def perform_update(self, serializer):
        instance = self.get_object()
        old_assigned_to = instance.assigned_to
        old_status = instance.status

        updated_instance = serializer.save()

        # Fire automation: TASK_UPDATED
        try:
            from .automation_engine import AutomationEngine
            AutomationEngine.process_event('TASK_UPDATED', updated_instance.project_id, task=updated_instance)
            if updated_instance.assigned_to != old_assigned_to:
                AutomationEngine.process_event('ASSIGNEE_CHANGED', updated_instance.project_id, task=updated_instance)
            if updated_instance.status_id != old_status.id:
                AutomationEngine.process_event('STATUS_CHANGED', updated_instance.project_id, task=updated_instance)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Automation error on update: {e}")

        # Fire plugin events
        try:
            from plugins import fire
            fire('on_task_updated', task=updated_instance)
            if updated_instance.assigned_to != old_assigned_to:
                fire('on_task_assigned', task=updated_instance, assignee=updated_instance.assigned_to)
            if updated_instance.status_id != old_status.id:
                fire('on_task_status_changed',
                     task=updated_instance,
                     old_status=old_status.category,
                     new_status=updated_instance.status.category)
        except Exception:
            pass

        # Handle Assigned_to Notifications
        if updated_instance.assigned_to and updated_instance.assigned_to != old_assigned_to:
            actor_user = self.request.user if self.request.user.is_authenticated else None
            if actor_user and actor_user.id != updated_instance.assigned_to.id:
                Notification.objects.create(
                    recipient=updated_instance.assigned_to,
                    actor=actor_user,
                    verb="assigned you to",
                    type="ASSIGNMENT",
                    task=updated_instance
                )

    @action(detail=True, methods=['post'], url_path='assign')
    def assign_task(self, request, pk=None):
        """Assign a task to a single user."""
        from tracker.models import User
        task = self.get_object()
        
        user_id = request.data.get('assigned_to')
        if not user_id:
            user_ids = request.data.get('assigned_to_ids', [])
            if user_ids:
                user_id = user_ids[0]

        actor_user = request.user if request.user.is_authenticated else None

        if user_id:
            try:
                user = User.objects.get(id=user_id)
                task.assigned_to = user
                in_progress = TaskStatus.objects.filter(project=task.project, category='IN_PROGRESS').first()
                if in_progress:
                    task.status = in_progress
                
                if actor_user and actor_user.id != user.id:
                    Notification.objects.create(
                        recipient=user,
                        actor=actor_user,
                        verb="assigned you to",
                        type="ASSIGNMENT",
                        task=task
                    )
            except User.DoesNotExist:
                task.assigned_to = None
        else:
            task.assigned_to = None
            todo = TaskStatus.objects.filter(project=task.project, category='TO_DO').first()
            if todo:
                task.status = todo
                
        task.save()

        # Fire automation: ASSIGNEE_CHANGED
        try:
            from .automation_engine import AutomationEngine
            AutomationEngine.process_event('ASSIGNEE_CHANGED', task.project_id, task=task)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Automation error on assign: {e}")

        serializer = self.get_serializer(task)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='update-watchers')
    def update_watchers(self, request, pk=None):
        from tracker.models import User
        task = self.get_object()
        watcher_ids = request.data.get('watcher_ids', [])
        
        users = User.objects.filter(id__in=watcher_ids)
        task.watchers.set(users)
        
        serializer = self.get_serializer(task)
        return Response(serializer.data)

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        import re
        user = self.request.user if self.request.user.is_authenticated else None
            
        if user:
            comment = serializer.save(author=user)
        else:
            comment = serializer.save()

        # Notify task assignee on comment
        if comment.task and comment.task.assigned_to and comment.task.assigned_to != comment.author:
            Notification.objects.create(
                recipient=comment.task.assigned_to,
                actor=comment.author if comment.author else comment.task.assigned_to,
                verb="commented on",
                type="COMMENT",
                task=comment.task
            )

        # Handle @mention notifications
        if comment.content and comment.author:
            from tracker.models import User
            mentioned_usernames = re.findall(r'@(\w+)', comment.content)
            for uname in set(mentioned_usernames):
                try:
                    mentioned_user = User.objects.get(username=uname)
                    if mentioned_user != comment.author:
                        Notification.objects.get_or_create(
                            recipient=mentioned_user,
                            actor=comment.author,
                            verb="mentioned you in",
                            type="MENTION",
                            task=comment.task
                        )
                except User.DoesNotExist:
                    pass

    def get_queryset(self):
        queryset = Comment.objects.select_related('author').prefetch_related('replies__author')
        task_id = self.request.query_params.get('task')
        if task_id:
            # Return only top-level comments; replies are nested inside
            queryset = queryset.filter(task_id=task_id, parent__isnull=True)
        return queryset.order_by('created_at')

class SubtaskViewSet(viewsets.ModelViewSet):
    queryset = Subtask.objects.all()
    serializer_class = SubtaskSerializer
    
    def get_queryset(self):
        queryset = Subtask.objects.select_related('assigned_to', 'status').all()
        task_id = self.request.query_params.get('task')
        if task_id:
            queryset = queryset.filter(parent_id=task_id)
        return queryset


class WorkLogViewSet(viewsets.ModelViewSet):
    queryset = WorkLog.objects.select_related('user', 'task').all()
    serializer_class = WorkLogSerializer

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        log = serializer.save(user=user)

        # Update task time_spent to sum of all logs
        task = log.task
        total = sum(wl.hours for wl in task.work_logs.all())
        task.time_spent = total
        task.save(update_fields=['time_spent'])

    def perform_destroy(self, instance):
        task = instance.task
        instance.delete()
        total = sum(wl.hours for wl in task.work_logs.all())
        task.time_spent = total
        task.save(update_fields=['time_spent'])

    def get_queryset(self):
        qs = super().get_queryset()
        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs

@api_view(['GET'])
@permission_classes([CanViewReports])
def project_bottleneck(request, project_id):
    """
    Analyze bottlenecks in a project:
    - Overloaded assignees (too many IN_PROGRESS tasks)
    - Blocked tasks (has BLOCKS incoming links)
    - Overdue tasks (past end_date, not DONE)
    - Stale tasks (IN_PROGRESS but no activity for N days)
    - Status columns with too many tasks (WIP limit exceeded)
    - Unassigned high-priority tasks
    """
    from django.utils import timezone
    from django.db.models import Count, Q
    from datetime import timedelta

    now = timezone.now()
    stale_threshold = int(request.query_params.get('stale_days', 7))

    tasks_qs = Task.objects.select_related(
        'assigned_to', 'status', 'epic', 'sprint'
    ).prefetch_related('incoming_links').filter(project_id=project_id)

    all_tasks = list(tasks_qs)

    # ── 1. Overloaded Assignees ───────────────────────────────────────────────
    assignee_map = {}
    for t in all_tasks:
        if t.assigned_to and t.status.category == 'IN_PROGRESS':
            uid = t.assigned_to.id
            if uid not in assignee_map:
                assignee_map[uid] = {'username': t.assigned_to.username, 'count': 0, 'tasks': []}
            assignee_map[uid]['count'] += 1
            assignee_map[uid]['tasks'].append({'id': t.id, 'title': t.title, 'priority': t.priority})

    overloaded_threshold = int(request.query_params.get('overload_threshold', 3))
    overloaded = [v for v in assignee_map.values() if v['count'] >= overloaded_threshold]
    overloaded.sort(key=lambda x: x['count'], reverse=True)

    # ── 2. Blocked Tasks ─────────────────────────────────────────────────────
    blocked_tasks = []
    for t in all_tasks:
        if t.status.category != 'DONE':
            blocking_links = [l for l in t.incoming_links.all() if l.type == 'BLOCKS']
            if blocking_links:
                blocked_tasks.append({
                    'id': t.id,
                    'title': t.title,
                    'priority': t.priority,
                    'assignee': t.assigned_to.username if t.assigned_to else None,
                    'blocked_by_count': len(blocking_links),
                })

    # ── 3. Overdue Tasks ─────────────────────────────────────────────────────
    overdue_tasks = []
    for t in all_tasks:
        if t.end_date and t.end_date < now and t.status.category != 'DONE':
            days_overdue = (now - t.end_date).days
            overdue_tasks.append({
                'id': t.id,
                'title': t.title,
                'priority': t.priority,
                'assignee': t.assigned_to.username if t.assigned_to else None,
                'days_overdue': days_overdue,
                'end_date': t.end_date.isoformat(),
            })
    overdue_tasks.sort(key=lambda x: x['days_overdue'], reverse=True)

    # ── 4. Stale Tasks (IN_PROGRESS, no update for N days) ───────────────────
    stale_cutoff = now - timedelta(days=stale_threshold)
    stale_tasks = []
    for t in all_tasks:
        if t.status.category == 'IN_PROGRESS' and t.created_at < stale_cutoff:
            days_stale = (now - t.created_at).days
            stale_tasks.append({
                'id': t.id,
                'title': t.title,
                'priority': t.priority,
                'assignee': t.assigned_to.username if t.assigned_to else None,
                'days_stale': days_stale,
                'status_name': t.status.name,
            })
    stale_tasks.sort(key=lambda x: x['days_stale'], reverse=True)

    # ── 5. WIP per Status Column ─────────────────────────────────────────────
    status_wip = {}
    for t in all_tasks:
        if t.status.category != 'DONE':
            sid = t.status.id
            if sid not in status_wip:
                status_wip[sid] = {
                    'status_name': t.status.name,
                    'category': t.status.category,
                    'color': t.status.color,
                    'count': 0,
                }
            status_wip[sid]['count'] += 1

    wip_limit = int(request.query_params.get('wip_limit', 5))
    wip_exceeded = [v for v in status_wip.values() if v['count'] > wip_limit]
    wip_exceeded.sort(key=lambda x: x['count'], reverse=True)
    all_wip = sorted(status_wip.values(), key=lambda x: x['count'], reverse=True)

    # ── 6. Unassigned High-Priority Tasks ────────────────────────────────────
    unassigned_high = [
        {'id': t.id, 'title': t.title, 'priority': t.priority, 'status': t.status.name}
        for t in all_tasks
        if t.assigned_to is None and t.priority == 'HIGH' and t.status.category != 'DONE'
    ]

    # ── Summary Score (0–100, lower = more bottlenecks) ──────────────────────
    total = len(all_tasks) or 1
    penalty = (
        len(overloaded) * 10 +
        len(blocked_tasks) * 8 +
        min(len(overdue_tasks), 10) * 6 +
        min(len(stale_tasks), 10) * 4 +
        len(wip_exceeded) * 5 +
        len(unassigned_high) * 3
    )
    health_score = max(0, 100 - penalty)

    return Response({
        'health_score': health_score,
        'overloaded_assignees': overloaded,
        'blocked_tasks': blocked_tasks,
        'overdue_tasks': overdue_tasks,
        'stale_tasks': stale_tasks,
        'wip_columns': all_wip,
        'wip_exceeded': wip_exceeded,
        'unassigned_high_priority': unassigned_high,
        'config': {
            'overload_threshold': overloaded_threshold,
            'stale_days': stale_threshold,
            'wip_limit': wip_limit,
        }
    })


@api_view(['GET'])
@permission_classes([CanViewReports])
def project_velocity(request, project_id):
    """
    Return velocity history for all completed sprints in a project.
    """
    sprints = Sprint.objects.filter(
        project_id=project_id,
        status='COMPLETED'
    ).order_by('completed_at', 'created_at')

    data = []
    for s in sprints:
        completion_rate = round(
            (s.completed_tasks / s.total_tasks * 100) if s.total_tasks > 0 else 0, 1
        )
        point_rate = round(
            (s.completed_points / s.committed_points * 100) if s.committed_points > 0 else 0, 1
        )
        data.append({
            'id':               s.id,
            'name':             s.name,
            'committed_points': s.committed_points,
            'completed_points': s.completed_points,
            'total_tasks':      s.total_tasks,
            'completed_tasks':  s.completed_tasks,
            'completion_rate':  completion_rate,
            'point_rate':       point_rate,
            'completed_at':     s.completed_at.isoformat() if s.completed_at else None,
        })

    recent = data[-3:] if len(data) >= 3 else data
    avg_velocity = round(
        sum(s['completed_points'] for s in recent) / len(recent), 1
    ) if recent else 0

    return Response({
        'sprints':       data,
        'avg_velocity':  avg_velocity,
        'total_sprints': len(data),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_users(request):
    from tracker.models import User
    from tracker.serializers import UserSerializer
    from django.db.models import Q
    
    project_name = request.query_params.get('project_name')
    if not project_name:
        return Response([])
    
    query = (
        Q(primary_project__name=project_name) | 
        Q(project_roles__project__name=project_name) | 
        Q(project__name=project_name)
    )
    
    users = User.objects.filter(query).distinct()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def update_task_status(request, pk):
    """
    Update task status with transition validation.
    """
    try:
        task = Task.objects.get(pk=pk)
        new_status_id = request.data.get('status_id')
        if not new_status_id:
            return Response({'error': 'status_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        new_status = TaskStatus.objects.get(pk=new_status_id)
        
        # Check transition rules
        current_status = task.status
        if current_status.id == new_status.id:
            return Response({'status': 'no change'})

        # Find rules for this project
        rules = WorkflowTransition.objects.filter(project=task.project)
        if rules.exists():
            # If rules exist, we must follow them
            has_valid_rule = rules.filter(
                (models.Q(from_status=current_status) | models.Q(from_status__isnull=True)),
                to_status=new_status
            ).exists()
            
            if not has_valid_rule:
                return Response({
                    'error': f'Transition from {current_status.name} to {new_status.name} is not allowed.'
                }, status=status.HTTP_400_BAD_REQUEST)

        task.status = new_status
        task.save()

        # Fire automation: STATUS_CHANGED
        try:
            from .automation_engine import AutomationEngine
            AutomationEngine.process_event('STATUS_CHANGED', task.project_id, task=task)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Automation error on status change: {e}")
        
        # Create notification for assignee
        if task.assigned_to:
            actor_user = request.user if request.user.is_authenticated else None
                
            if actor_user and actor_user.id != task.assigned_to.id:
                Notification.objects.create(
                    recipient=task.assigned_to,
                    actor=actor_user,
                    verb="changed status of",
                    type="STATUS_CHANGE",
                    task=task
                )

        return Response(TaskSerializer(task).data)
        
    except Task.DoesNotExist:
        return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
    except TaskStatus.DoesNotExist:
        return Response({'error': 'Status not found'}, status=status.HTTP_404_NOT_FOUND)

class ProjectMessageViewSet(viewsets.ModelViewSet):
    queryset = ProjectMessage.objects.all()
    serializer_class = ProjectMessageSerializer
    permission_classes = [CanViewChat]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        project_id = self.request.query_params.get('project')
        if project_id:
            return ProjectMessage.objects.filter(project_id=project_id)
        return ProjectMessage.objects.all()

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(sender=user)

from .models import Documentation, DocumentRevision
from .serializers import DocumentationSerializer, DocumentRevisionSerializer

from .models import Documentation, DocumentRevision
from .serializers import DocumentationSerializer, DocumentRevisionSerializer, DocTagSerializer

class DocTagViewSet(viewsets.ModelViewSet):
    serializer_class = DocTagSerializer
    permission_classes = [CanViewDocs]

    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return DocTag.objects.filter(project_id=project_id)
        return DocTag.objects.none()


class DocumentationViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentationSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [CanCreateDoc()]
        if self.action in ('update', 'partial_update', 'reorder', 'copy_doc', 'move_doc'):
            return [CanEditDoc()]
        if self.action == 'destroy':
            return [CanDeleteDoc()]
        return [CanViewDocs()]

    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        tag = self.request.query_params.get('tag')
        qs = Documentation.objects.filter(is_published=True).order_by('order', 'created_at')
        if project_id:
            qs = qs.filter(project_id=project_id)
        if tag:
            qs = qs.filter(tags__id=tag)
        return qs

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        doc = serializer.save(created_by=user)
        DocumentRevision.objects.create(document=doc, content=doc.content, edited_by=user)
        try:
            from plugins import fire
            fire('on_doc_created', doc=doc)
        except Exception:
            pass

    def perform_update(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        doc = serializer.save()
        DocumentRevision.objects.create(document=doc, content=doc.content, edited_by=user)
        try:
            from plugins import fire
            fire('on_doc_updated', doc=doc)
        except Exception:
            pass

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        document = self.get_object()
        revisions = document.revisions.all()
        return Response(DocumentRevisionSerializer(revisions, many=True).data)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """Bulk update order for drag-and-drop. Body: [{id, order, parent}]"""
        items = request.data.get('items', [])
        for item in items:
            Documentation.objects.filter(id=item['id']).update(
                order=item.get('order', 0),
                parent_id=item.get('parent')
            )
        return Response({'status': 'reordered'})

    @action(detail=True, methods=['post'], url_path='copy')
    def copy_doc(self, request, pk=None):
        """Copy document to another project (or same). Body: {target_project_id}"""
        doc = self.get_object()
        target_project_id = request.data.get('target_project_id', doc.project_id)
        user = request.user if request.user.is_authenticated else None

        new_doc = Documentation.objects.create(
            project_id=target_project_id,
            parent=None,
            title=f"{doc.title} (نسخة)",
            content=doc.content,
            is_published=doc.is_published,
            order=doc.order,
            created_by=user,
        )
        new_doc.tags.set(doc.tags.all())
        return Response(DocumentationSerializer(new_doc).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='move')
    def move_doc(self, request, pk=None):
        """Move document to another project. Body: {target_project_id}"""
        doc = self.get_object()
        target_project_id = request.data.get('target_project_id')
        if not target_project_id:
            return Response({'error': 'target_project_id required'}, status=400)
        doc.project_id = target_project_id
        doc.parent = None
        doc.save(update_fields=['project', 'parent'])
        return Response(DocumentationSerializer(doc).data)

from .models import DocComment
from .serializers import DocCommentSerializer

class DocCommentViewSet(viewsets.ModelViewSet):
    serializer_class = DocCommentSerializer
    permission_classes = [CanViewDocs]

    def get_queryset(self):
        doc_id = self.request.query_params.get('document')
        if doc_id:
            return DocComment.objects.filter(document_id=doc_id).select_related('author')
        return DocComment.objects.none()

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(author=user)

    def perform_destroy(self, instance):
        user = self.request.user
        if instance.author == user or (user and user.is_superuser):
            instance.delete()


class APIEndpointViewSet(viewsets.ModelViewSet):
    serializer_class = APIEndpointSerializer
    pagination_class = None
    permission_classes = [CanViewDocs]

    def get_queryset(self):
        project_id = self.request.query_params.get('project')
        if project_id:
            return APIEndpoint.objects.filter(project_id=project_id)
        return APIEndpoint.objects.all()

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def project_api_extract(request, project_id):
    """
    Receives a ZIP file containing a Django project, extracts it,
    analyzes urls.py and views.py files, and generates a new Documentation entry.
    """
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

    zip_file = request.FILES['file']
    
    # Save the file temporarily
    temp_dir = tempfile.gettempdir()
    temp_zip_path = os.path.join(temp_dir, zip_file.name)
    
    with open(temp_zip_path, 'wb+') as destination:
        for chunk in zip_file.chunks():
            destination.write(chunk)

    try:
        # Check Project existence
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return Response({'error': 'Project not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Extract APIs
        apis = analyze_django_zip(temp_zip_path)

        # Bulk create structured API endpoints
        existing_endpoints = APIEndpoint.objects.filter(project=project)
        existing_map = {
            (ep.app_name, ep.path, ep.method): ep for ep in existing_endpoints
        }
        
        processed_keys = set()
        new_endpoints = []
        endpoints_to_update = []

        for api in apis:
            app_name = api.get('app', 'N/A')
            path = api.get('path', '/')
            method = api.get('method', 'GET')
            description = api.get('description', '')
            
            key = (app_name, path, method)
            processed_keys.add(key)
            
            if key in existing_map:
                ep = existing_map[key]
                ep.description = description
                endpoints_to_update.append(ep)
            else:
                new_endpoints.append(
                    APIEndpoint(
                        project=project,
                        app_name=app_name,
                        path=path,
                        method=method,
                        description=description
                    )
                )
        
        # Bulk create new
        if new_endpoints:
            APIEndpoint.objects.bulk_create(new_endpoints)
            
        # Bulk update existing (only updating description to preserve notes)
        if endpoints_to_update:
            APIEndpoint.objects.bulk_update(endpoints_to_update, ['description'])
            
        # Delete endpoints that no longer exist in code
        keys_to_delete = set(existing_map.keys()) - processed_keys
        if keys_to_delete:
            ids_to_delete = [existing_map[k].id for k in keys_to_delete]
            APIEndpoint.objects.filter(id__in=ids_to_delete).delete()

        return Response({'message': 'تم استخراج الواجهات بنجاح.', 'count': len(apis)}, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        # Cleanup
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)


# ─── Evaluation System ViewSets ───────────────────────────────────────────────

class EvaluationPeriodViewSet(viewsets.ModelViewSet):
    queryset = EvaluationPeriod.objects.all()
    serializer_class = EvaluationPeriodSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [CanManageEvaluations()]
        return [CanViewEvaluations()]

    def get_queryset(self):
        qs = EvaluationPeriod.objects.all()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    @action(detail=False, methods=['post'], url_path='generate-year')
    def generate_year(self, request):
        """
        Generate 12 monthly evaluation periods for a given year.
        Expects {"year": 2026, "project": <optional_id>} in request body.
        """
        year_str = request.data.get('year')
        project_id = request.data.get('project')
        
        try:
            year = int(year_str)
        except (TypeError, ValueError):
            return Response({"detail": "Valid year is required."}, status=400)
            
        import calendar
        from datetime import date
        from project_management.models import Project

        project_obj = None
        if project_id:
            from django.shortcuts import get_object_or_404
            project_obj = get_object_or_404(Project, pk=project_id)

        created_count = 0
        month_names = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
            5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
            9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
        }

        for month in range(1, 13):
            month_name = month_names[month]
            period_name = f"{month_name} {year}"
            
            # Start and end date for the month
            start_dt = date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end_dt = date(year, month, last_day)

            # Insert only if not already exists for the same name and project
            obj, created = EvaluationPeriod.objects.get_or_create(
                name=period_name,
                project=project_obj,
                defaults={
                    'start_date': start_dt,
                    'end_date': end_dt,
                }
            )
            if created:
                created_count += 1
                
        return Response({
            "detail": f"Generated {created_count} periods for the year {year}.",
            "created": created_count
        })


class KPIViewSet(viewsets.ModelViewSet):
    queryset = KPI.objects.filter(is_active=True)
    serializer_class = KPISerializer
    permission_classes = [CanViewEvaluations]

    def get_queryset(self):
        qs = KPI.objects.filter(is_active=True)
        kpi_type = self.request.query_params.get('type')
        if kpi_type:
            qs = qs.filter(type=kpi_type)
        return qs


class UserEvaluationViewSet(viewsets.ModelViewSet):
    queryset = UserEvaluation.objects.select_related('user', 'period').prefetch_related('details__kpi')
    serializer_class = UserEvaluationSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [CanManageEvaluations()]
        return [CanViewEvaluations()]

    def get_queryset(self):
        qs = UserEvaluation.objects.select_related('user', 'period').prefetch_related('details__kpi')
        period_id = self.request.query_params.get('period')
        user      = self.request.user
        
        if period_id:
            qs = qs.filter(period_id=period_id)
        
        # Non-superusers can only see their own evaluations
        # unless 'all' param is explicitly passed (for managers viewing team)
        show_all = self.request.query_params.get('all', 'false').lower() == 'true'
        if user and user.is_authenticated and not user.is_superuser and not show_all:
            qs = qs.filter(user=user)
        
        return qs

    @action(detail=True, methods=['post'], url_path='calculate-metrics')
    def calculate_metrics(self, request, pk=None):
        """
        Auto-compute AUTOMATED KPI scores from this user's tasks
        within the evaluation period date range, then recalculate
        the weighted composite score and Gamification points.
        """
        evaluation = self.get_object()
        user   = evaluation.user
        period = evaluation.period

        # Count tasks that were COMPLETED (end_date) within the evaluation period
        # OR tasks created during the period (if no end_date set yet).
        # Using end_date gives a more accurate picture of work done within the period.
        from django.db.models import Q
        tasks = Task.objects.filter(
            assigned_to=user,
        ).filter(
            Q(end_date__date__gte=period.start_date, end_date__date__lte=period.end_date) |
            Q(end_date__isnull=True, created_at__date__gte=period.start_date, created_at__date__lte=period.end_date)
        ).select_related('status')

        total = tasks.count()
        if total == 0:
            # If no tasks, score is 0, just save and return
            evaluation.score = 0.0
            evaluation.points = 0
            evaluation.save()
            eval_with_relations = self.get_queryset().get(pk=evaluation.pk)
            return Response(UserEvaluationSerializer(eval_with_relations).data)

        done_tasks      = tasks.filter(status__category='DONE')
        done_count      = done_tasks.count()
        on_time_count   = 0
        lead_time_total = 0.0
        bug_count       = tasks.filter(issue_type='BUG').count()

        for t in done_tasks:
            if t.end_date and t.created_at:
                delta = (t.end_date - t.created_at).total_seconds() / 3600
                lead_time_total += delta
                if t.end_date.date() <= period.end_date:
                    on_time_count += 1

        completion_rate  = (done_count / total) * 100
        on_time_rate     = (on_time_count / done_count * 100) if done_count > 0 else 0
        avg_lead_time_h  = (lead_time_total / done_count) if done_count > 0 else 0
        bug_rate         = (bug_count / total) * 100
        # Lead-time score: 0h -> 100pts, >=240h (10 days) -> 0pts (linear)
        lead_time_score  = max(0, 100 - (avg_lead_time_h / 240) * 100)

        # Build scores by KPI name (case-insensitive, stripped) for robustness
        kpi_scores_map = {
            'completion rate':  completion_rate,
            'on-time delivery': on_time_rate,
            'lead time':        lead_time_score,
            'bug rate':         max(0, 100 - bug_rate * 5),
        }

        total_weight = 0.0
        weighted_sum = 0.0

        automated_kpis = KPI.objects.filter(is_active=True, type='AUTOMATED')
        for kpi in automated_kpis:
            # Match by lowercase+stripped name so minor DB naming differences don't break scoring
            raw_score = kpi_scores_map.get(kpi.name.strip().lower())
            if raw_score is None:
                continue
            raw_score = max(0.0, min(100.0, raw_score))
            EvaluationDetail.objects.update_or_create(
                evaluation=evaluation, kpi=kpi,
                defaults={
                    'score': raw_score,
                    'raw_value': f"{raw_score:.1f}",
                }
            )
            weighted_sum += raw_score * kpi.weight
            total_weight += kpi.weight

        # Include already-entered MANUAL KPI scores
        for d in evaluation.details.filter(kpi__type='MANUAL'):
            weighted_sum += d.score * d.kpi.weight
            total_weight += d.kpi.weight

        composite = (weighted_sum / total_weight) if total_weight > 0 else 0.0
        points    = on_time_count * 10 - bug_count * 5

        evaluation.score  = round(composite, 2)
        evaluation.points = max(0, points)
        evaluation.save()

        # Re-fetch from DB to ensure all relations (user.username, period.name) are populated
        eval_with_relations = self.get_queryset().get(pk=evaluation.pk)
        return Response(UserEvaluationSerializer(eval_with_relations).data)


class EvaluationDetailViewSet(viewsets.ModelViewSet):
    queryset = EvaluationDetail.objects.select_related('kpi', 'evaluation')
    serializer_class = EvaluationDetailSerializer
    permission_classes = [CanViewEvaluations]

    def get_queryset(self):
        qs = EvaluationDetail.objects.select_related('kpi', 'evaluation')
        eval_id = self.request.query_params.get('evaluation')
        if eval_id:
            qs = qs.filter(evaluation_id=eval_id)
        return qs

# ─── System Technical Design New Modules ──────────────────────────────────────

from .models import (
    CustomField, CustomFieldOption, TaskCustomFieldValue,
    AutomationRule, AutomationTrigger, AutomationCondition, AutomationAction,
    Version, ReleaseNote, TaskVersion, PluginModel
)
from .serializers import (
    CustomFieldSerializer, CustomFieldOptionSerializer, TaskCustomFieldValueSerializer,
    AutomationRuleSerializer, AutomationTriggerSerializer, AutomationConditionSerializer, AutomationActionSerializer,
    VersionSerializer, ReleaseNoteSerializer, TaskVersionSerializer, PluginModelSerializer
)

class CustomFieldViewSet(viewsets.ModelViewSet):
    queryset = CustomField.objects.all()
    serializer_class = CustomFieldSerializer
    permission_classes = [CanViewSettings]

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

class CustomFieldOptionViewSet(viewsets.ModelViewSet):
    queryset = CustomFieldOption.objects.all()
    serializer_class = CustomFieldOptionSerializer
    permission_classes = [CanViewSettings]

class TaskCustomFieldValueViewSet(viewsets.ModelViewSet):
    queryset = TaskCustomFieldValue.objects.all()
    serializer_class = TaskCustomFieldValueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs

class AutomationRuleViewSet(viewsets.ModelViewSet):
    queryset = AutomationRule.objects.all()
    serializer_class = AutomationRuleSerializer
    permission_classes = [CanViewSettings]

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

class AutomationTriggerViewSet(viewsets.ModelViewSet):
    queryset = AutomationTrigger.objects.all()
    serializer_class = AutomationTriggerSerializer
    permission_classes = [CanViewSettings]

class AutomationConditionViewSet(viewsets.ModelViewSet):
    queryset = AutomationCondition.objects.all()
    serializer_class = AutomationConditionSerializer
    permission_classes = [CanViewSettings]

class AutomationActionViewSet(viewsets.ModelViewSet):
    queryset = AutomationAction.objects.all()
    serializer_class = AutomationActionSerializer
    permission_classes = [CanViewSettings]

class VersionViewSet(viewsets.ModelViewSet):
    queryset = Version.objects.all()
    serializer_class = VersionSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [CanManageReleases()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

class ReleaseNoteViewSet(viewsets.ModelViewSet):
    queryset = ReleaseNote.objects.all()
    serializer_class = ReleaseNoteSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [CanManageReleases()]
        return [IsAuthenticated()]

class TaskVersionViewSet(viewsets.ModelViewSet):
    queryset = TaskVersion.objects.all()
    serializer_class = TaskVersionSerializer
    permission_classes = [IsAuthenticated]

class PluginModelViewSet(viewsets.ModelViewSet):
    queryset = PluginModel.objects.all()
    serializer_class = PluginModelSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        instance = serializer.save()
        try:
            from plugins import reload_plugin, unload_plugin
            if instance.enabled:
                reload_plugin(instance.name)
            else:
                unload_plugin(instance.name)
        except Exception:
            pass

    def perform_destroy(self, instance):
        try:
            from plugins import unload_plugin
            unload_plugin(instance.name)
        except Exception:
            pass
        instance.delete()

    @action(detail=False, methods=['get'], url_path='loaded')
    def loaded(self, request):
        """Return list of currently loaded (active) plugin names."""
        try:
            from plugins import get_loaded
            return Response({'loaded': get_loaded()})
        except Exception:
            return Response({'loaded': []})
