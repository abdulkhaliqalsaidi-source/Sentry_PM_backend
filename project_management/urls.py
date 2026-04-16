from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectViewSet, TaskViewSet, CommentViewSet, SubtaskViewSet,
    SprintViewSet, EpicViewSet, LabelViewSet, ProjectRoleViewSet, AttachmentViewSet, 
    IssueLinkViewSet, project_users, all_users_list, TaskStatusViewSet, WorkflowTransitionViewSet,
    update_task_status, NotificationViewSet, ProjectMessageViewSet, DocumentationViewSet,
    project_api_extract, APIEndpointViewSet, upload_doc_image, DocCommentViewSet,
    DocTagViewSet,
    EvaluationPeriodViewSet, KPIViewSet, UserEvaluationViewSet, EvaluationDetailViewSet,
    CustomFieldViewSet, CustomFieldOptionViewSet, TaskCustomFieldValueViewSet,
    AutomationRuleViewSet, AutomationTriggerViewSet, AutomationConditionViewSet, AutomationActionViewSet,
    VersionViewSet, ReleaseNoteViewSet, TaskVersionViewSet, PluginModelViewSet,
    WorkLogViewSet, project_bottleneck, project_velocity
)
router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'subtasks', SubtaskViewSet)
router.register(r'work-logs', WorkLogViewSet, basename='worklog')
router.register(r'sprints', SprintViewSet)
router.register(r'epics', EpicViewSet)
router.register(r'labels', LabelViewSet, basename='label')
router.register(r'project-roles', ProjectRoleViewSet)
router.register(r'attachments', AttachmentViewSet)
router.register(r'issue-links', IssueLinkViewSet)
router.register(r'statuses', TaskStatusViewSet)
router.register(r'transitions', WorkflowTransitionViewSet)
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'messages', ProjectMessageViewSet)
router.register(r'docs', DocumentationViewSet, basename='documentation')
router.register(r'doc-comments', DocCommentViewSet, basename='doccomment')
router.register(r'doc-tags', DocTagViewSet, basename='doctag')
router.register(r'endpoints', APIEndpointViewSet, basename='apiendpoint')
router.register(r'eval-periods', EvaluationPeriodViewSet, basename='evalperiod')
router.register(r'kpis', KPIViewSet, basename='kpi')
router.register(r'evaluations', UserEvaluationViewSet, basename='evaluation')
router.register(r'eval-details', EvaluationDetailViewSet, basename='evaldetail')
router.register(r'custom-fields', CustomFieldViewSet)
router.register(r'custom-field-options', CustomFieldOptionViewSet)
router.register(r'task-custom-field-values', TaskCustomFieldValueViewSet)
router.register(r'automation-rules', AutomationRuleViewSet)
router.register(r'automation-triggers', AutomationTriggerViewSet)
router.register(r'automation-conditions', AutomationConditionViewSet)
router.register(r'automation-actions', AutomationActionViewSet)
router.register(r'versions', VersionViewSet)
router.register(r'release-notes', ReleaseNoteViewSet)
router.register(r'task-versions', TaskVersionViewSet)
router.register(r'plugins', PluginModelViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('project-users/', project_users, name='project_users'),
    path('all-users/', all_users_list, name='all_users_list'),
    path('tasks/<int:pk>/update-status/', update_task_status, name='update_task_status'),
    path('projects/<int:project_id>/extract-api/', project_api_extract, name='project_api_extract'),
    path('projects/<int:project_id>/bottleneck/', project_bottleneck, name='project_bottleneck'),
    path('projects/<int:project_id>/velocity/', project_velocity, name='project_velocity'),
    path('upload-image/', upload_doc_image, name='upload_doc_image'),
]
