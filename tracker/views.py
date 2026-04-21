import json
from django.core.management import call_command
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
import os
import shutil

from .models import Issue, Event, Session, Project, User, PermissionGroup
from .serializers import IssueSerializer, EventSerializer, SessionSerializer, UserSerializer, ProjectSerializer, PermissionGroupSerializer
from .utils import generate_hash
from rest_framework_simplejwt.tokens import RefreshToken
from .rate_limit import rate_limit

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@rate_limit(requests=60, window=60, key_prefix='capture')
def capture_error(request):
    try:
        data = request.data
        # Extract data
        error_type = data.get('type', 'Unknown Error')
        message = data.get('message', '')
        traceback_str = data.get('stack', '')
        provided_project = data.get('project') or 'General' # Handle None or empty string
        url = data.get('url', '')
        
        # --- Port-Based Monitoring Logic ---
        # Map certain ports to specific project names automatically
        PROJECT_PORTS = {
            'Frontend App': ['3000', '3001', '3002', '3003','5175'],
            'Dashboard': ['5173', '5174'],
            'Backend API': ['8000', '8001', '3131'],
        }
        
        project = provided_project
        
        # Only attempt to detect project from Port if the user didn't specify a custom one
        # "General" is our backend default, "Default Project" is the SDK default.
        if provided_project in ['General', 'Default Project', 'Frontend App']:
            if url:
                try:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(url)
                    port = str(parsed_url.port) if parsed_url.port else None
                    
                    if port is None:
                        if parsed_url.scheme == 'http': port = '80'
                        elif parsed_url.scheme == 'https': port = '443'
                        
                    if port:
                        for proj_name, ports in PROJECT_PORTS.items():
                            if port in ports:
                                project = proj_name
                                break
                        
                except Exception as e:
                    print(f"Error parsing URL port: {e}")

        # السحر هنا: إذا المشروع غير موجود، أنشئه فوراً
        project_obj, _ = Project.objects.get_or_create(
            name=project,
        )

        # Sync with Project Management App
        try:
            from project_management.models import Project as PMProject, TaskStatus as PMTaskStatus
            if not PMProject.objects.filter(name=project).exists():
                owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
                if owner:
                    pm_project = PMProject.objects.create(
                        name=project,
                        description=f"Auto-created from Sentry Tracker for {project}",
                        owner=owner
                    )
                    # FIX #9: create default TaskStatuses so Kanban/Backlog work
                    default_statuses = [
                        ('To Do',      '#64748b', 0, 'TO_DO'),
                        ('In Progress','#3b82f6', 1, 'IN_PROGRESS'),
                        ('In Review',  '#f59e0b', 2, 'IN_REVIEW'),
                        ('Done',       '#10b981', 3, 'DONE'),
                    ]
                    for name, color, order, category in default_statuses:
                        PMTaskStatus.objects.create(
                            project=pm_project,
                            name=name,
                            color=color,
                            order=order,
                            category=category,
                        )
        except Exception as e:
            print(f"Failed to sync PM Project: {e}")

        full_title = f"{error_type}: {message}"
        location_signature = f"{data.get('url', '')}:{data.get('line', '')}"
        
        # for NetworkError, use the message (which contains URL + Status) as the signature
        if error_type == 'NetworkError':
            location_signature = message
            
        error_hash = generate_hash(error_type, location_signature, project)

        issue, created = Issue.objects.get_or_create(
            hash_id=error_hash,
            defaults={
                'title': full_title,
                'project': project_obj,
            }
        )

        if not created:
            # FIX #3: use atomic F() expression to avoid race condition
            from django.db.models import F
            Issue.objects.filter(pk=issue.pk).update(
                counter=F('counter') + 1,
                project=project_obj
            )
            issue.refresh_from_db()

        # Automatic Task Creation in Project Management
        try:
            from project_management.models import Project as PMProject, Task as PMTask
            # Find the corresponding PM Project
            pm_project = PMProject.objects.filter(name=project).first()
            if pm_project:
                # Check if a task for this issue already exists
                if not PMTask.objects.filter(sentry_error_id=issue.id).exists():
                    PMTask.objects.create(
                        project=pm_project,
                        title=f"Fix: {error_type}",
                        description=f"Auto-generated task for Sentry Issue #{issue.id}\n\nMessage: {message}\nLocation: {location_signature}\n\nView details in Issues tab.",
                        priority='HIGH',
                        status='TODO',
                        sentry_error_id=issue.id,
                        issue_type='BUG'
                    )
                    print(f"Auto-created PM Task for Issue {issue.id}")
        except Exception as e:
            print(f"Failed to auto-create PM Task: {e}")

        # Handle session recording if provided
        session_id = data.get('session_id')
        session = None
        if session_id:
            try:
                session, _ = Session.objects.get_or_create(session_id=session_id)
                # Update network logs in session if present in this request
                if 'network_logs' in data:
                    session.network_logs = session.network_logs + data['network_logs'] if session.network_logs else data['network_logs']
                    session.save()
                if 'console_logs' in data:
                    session.console_logs = session.console_logs + data['console_logs'] if session.console_logs else data['console_logs']
                    session.save()
            except Exception as e:
                print(f"Error handling session {session_id}: {e}")
                session = None

        breadcrumbs = data.get('breadcrumbs', [])
        incoming_events_data = data.get('events', [])
        final_events_data = []

        if session:
            if incoming_events_data:
                try:
                    # Save incoming events directly — simple and reliable
                    session.events_data = incoming_events_data
                    session.save()
                    has_snap = any(e.get('type') == 2 for e in session.events_data)
                    print(f"Session {session_id}: {len(session.events_data)} events | hasSnapshot={has_snap}")
                except Exception as e:
                    print(f"Error updating session events: {e}")

            final_events_data = []

            # One Event per Issue — update session reference if needed
            existing_event = Event.objects.filter(issue=issue).first()
            if existing_event:
                if session and existing_event.session != session:
                    existing_event.session = session
                    existing_event.save(update_fields=['session'])
                return Response({
                    'status': 'success',
                    'issue_id': issue.id,
                    'project_id': project_obj.id,
                    'event_id': existing_event.id,
                    'message': 'Duplicate event ignored, counter incremented'
                }, status=status.HTTP_200_OK)

        else:
            # No session — save events directly on Event
            final_events_data = incoming_events_data
        
        try:
            event = Event.objects.create(
                issue=issue,
                session=session,
                user_ident=data.get('user', 'anonymous'),
                url=url,
                traceback=traceback_str,
                breadcrumbs=breadcrumbs,
                events_data=final_events_data,
                network_logs=data.get('network_logs', []),
                console_logs=data.get('console_logs', [])
            )
            print(f"Event created successfully: {event.id}")
        except Exception as e:
            print(f"CRITICAL: Failed to create Event for Issue {issue.id}: {e}")
            # We should probably return error, but Issue is already created.
            return Response({'status': 'partial_error', 'message': 'Issue created but Event failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'status': 'success',
            'issue_id': issue.id,
            'project_id': project_obj.id,
            'event_id': event.id
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def save_session(request):
    session_id = request.data.get('session_id')
    events = request.data.get('events', [])
    network_logs = request.data.get('network_logs', [])
    console_logs = request.data.get('console_logs', [])

    if not session_id:
        return Response({'error': 'Missing session_id'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        session, created = Session.objects.get_or_create(session_id=session_id)

        # Replace events with latest buffer (SDK sends only last 20s)
        if events:
            session.events_data = events

        # Append network logs
        if network_logs:
            session.network_logs = session.network_logs + network_logs if session.network_logs else network_logs

        # Append console logs
        if console_logs:
            session.console_logs = session.console_logs + console_logs if session.console_logs else console_logs

        if events or network_logs or console_logs:
            session.save()

        return Response({'status': 'success', 'events_count': len(events)}, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"Error saving session: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_session_data(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    response_data = {}

    session_logs = event.session.network_logs if (event.session and event.session.network_logs) else []
    event_logs = event.network_logs if event.network_logs else []
    session_console = event.session.console_logs if (event.session and event.session.console_logs) else []
    event_console = event.console_logs if event.console_logs else []

    response_data['network_logs'] = session_logs + event_logs
    response_data['console_logs'] = session_console + event_console

    if event.events_data:
        response_data['events'] = event.events_data
        response_data['session_id'] = event.session.session_id if event.session else 'unknown'
    elif event.session:
        response_data['events'] = event.session.events_data
        response_data['session_id'] = event.session.session_id
    else:
        response_data['events'] = []
        response_data['session_id'] = 'unknown'

    print(f"get_session_data: event={event_id} events={len(response_data['events'])} hasSnap={any(e.get('type')==2 for e in response_data['events'])}")
    return Response(response_data)



@api_view(['DELETE'])
def delete_issue(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    issue.delete()
    return Response({'status': 'success'}, status=status.HTTP_200_OK)

@api_view(['GET'])
def issue_list(request):
    project_id = request.query_params.get('project_id')
    project_name = request.query_params.get('project_name')
    
    issues = Issue.objects.all()
    
    if project_id:
        issues = issues.filter(project_id=project_id)
    elif project_name:
        issues = issues.filter(project__name=project_name)
    else:
        # Filter by user's associated projects
        user = request.user
        if not user.is_superuser:
            from project_management.models import Project as PMProject
            from django.db.models import Q
            
            pm_project_names = list(PMProject.objects.filter(
                Q(owner=user) | Q(roles__user=user)
            ).values_list('name', flat=True))
            
            if user.primary_project and user.primary_project.name not in pm_project_names:
                pm_project_names.append(user.primary_project.name)
            
            if pm_project_names:
                issues = issues.filter(project__name__in=pm_project_names)
            else:
                issues = issues.none()
            
    issues = issues.order_by('-last_seen')
    serializer = IssueSerializer(issues, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def event_list(request):
    events = Event.objects.select_related('issue', 'session').order_by('-timestamp')
    serializer = EventSerializer(events, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_events_for_issue(request, issue_id):
    # Return only the canonical first event (oldest) for an issue.
    # The total occurrence count comes from the Issue.counter field.
    issue = get_object_or_404(Issue, id=issue_id)
    first_event = Event.objects.filter(issue_id=issue_id).select_related('session').order_by('timestamp').first()
    
    if not first_event:
        return Response([])
    
    serializer = EventSerializer(first_event)
    # Return as a list with a single item, plus total_count on the item
    data = serializer.data
    data['total_count'] = issue.counter
    return Response([data])

# Legacy dashboard view - keeping it for now until frontend is replaced
def dashboard(request):
    return render(request, 'tracker/dashboard.html')

def test_client(request):
    users = [
        {'id': 1, 'name': 'Alice Johnson', 'email': 'alice@example.com', 'role': 'Admin', 'bio': 'System Administrator'},
        {'id': 2, 'name': 'Bob Smith', 'email': 'bob@example.com', 'role': 'Editor', 'bio': 'Content Creator'},
        {'id': 3, 'name': 'Charlie Brown', 'email': 'charlie@example.com', 'role': 'Viewer', 'bio': 'Just looking around'},
    ]
    context = {'users': users}
    if request.method == 'POST':
        try:
            raise Exception("Simulated Server Error: Something went wrong while saving the profile!")
        except Exception as e:
             context['error'] = f"Error saving profile: {str(e)}"
    return render(request, 'tracker/test_client.html', context)

def serve_sdk(request):
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'client_sdk.js')
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/javascript')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    except FileNotFoundError:
        return HttpResponse('SDK file not found', status=404)

def serve_test_simulator(request):
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'public', 'test_simulator.html')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/html')
    except FileNotFoundError:
        return HttpResponse('test_simulator.html not found', status=404)

def serve_rrweb(request):
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'public', 'libs', 'rrweb.min.js')
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type='application/javascript')
    except FileNotFoundError:
        return HttpResponse('rrweb file not found', status=404)

# 2. API عام لعرض قائمة المشاريع في شاشة التسجيل
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def public_project_list(request):
    projects = Project.objects.all().values('id', 'name')
    return Response(projects)

# 3. API لتسجيل مستخدم جديد
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@rate_limit(requests=3, window=300, key_prefix='register')
def register_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    project_id = request.data.get('project_id')

    if User.objects.filter(username=username).exists():
        return Response({"error": "المستخدم موجود مسبقاً"}, status=400)

    user = User.objects.create_user(username=username, password=password)
    
    if project_id:
        try:
            project = Project.objects.get(id=project_id)
            user.primary_project = project
            user.save()
        except Project.DoesNotExist:
            user.delete() # Rollback user creation
            return Response({"error": "المشروع المحدد غير موجود"}, status=400)

    return Response({"status": "created", "user_id": user.id})

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@rate_limit(requests=5, window=60, key_prefix='login')
def login_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    if user:
        refresh = RefreshToken.for_user(user)
        serializer = UserSerializer(user)
        return Response({
            "status": "success",
            "username": user.username,
            "is_superuser": user.is_superuser,
            "group_name": serializer.data.get('group_name'),
            "project_id": user.primary_project.id if user.primary_project else None,
            "project_name": user.primary_project.name if user.primary_project else "General",
            "permissions": serializer.data.get('permissions'),
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })
    return Response({"error": "Invalid credentials"}, status=400)

@api_view(['GET'])
def get_profile(request):
    # FIX #2: users can only fetch own profile; superusers can fetch any
    username = request.query_params.get('username')
    if username:
        if request.user.is_superuser or request.user.username == username:
            user = get_object_or_404(User, username=username)
        else:
            return Response({"error": "غير مصرح لك بعرض هذا الملف الشخصي"}, status=403)
    else:
        user = request.user
    
    # FIX #2b: only superusers get all projects; others get their own only
    if request.user.is_superuser:
        projects = Project.objects.all()
    else:
        own_projects = Project.objects.filter(developers=user)
        primary = Project.objects.filter(pk=user.primary_project.pk) if user.primary_project else Project.objects.none()
        projects = (own_projects | primary).distinct()

    user_serializer = UserSerializer(user)
    projects_serializer = ProjectSerializer(projects.distinct(), many=True)
    
    return Response({
        "user": user_serializer.data,
        "all_projects": projects_serializer.data
    })

@api_view(['POST'])
def update_profile(request):
    # Users can only update their own profile; superusers can update any
    target_username = request.data.get('oldUsername') or request.data.get('username')
    
    if request.user.is_superuser and target_username:
        user = get_object_or_404(User, username=target_username)
    else:
        user = request.user
    
    # Update credentials if provided
    new_password = request.data.get('password')
    if new_password and new_password.strip():
        user.set_password(new_password)

    # FIX #1: 'current_username' was undefined — now correctly reads new username from request
    new_username = request.data.get('newUsername') or request.data.get('username')
    original_username = target_username or user.username
    if new_username and new_username != original_username:
        # Check if new username is already taken
        if User.objects.filter(username=new_username).exists():
            return Response({"error": "اسم المستخدم هذا مأخوذ بالفعل"}, status=400)
        user.username = new_username
    
    # Update Project if provided
    new_project_id = request.data.get('projectId')
    if new_project_id:
        try:
            project_obj = Project.objects.get(id=new_project_id)
            user.primary_project = project_obj
        except Project.DoesNotExist:
            pass
    
    # Update other fields
    user.first_name = request.data.get('firstName', user.first_name)
    user.last_name = request.data.get('lastName', user.last_name)
    user.email = request.data.get('email', user.email)
    
    # Handle avatar upload
    if 'avatar' in request.FILES:
        user.avatar = request.FILES['avatar']
    
    user.save()
    
    serializer = UserSerializer(user)
    return Response({
        "status": "success",
        "user": serializer.data
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_users(request):
    users = User.objects.all().order_by('-date_joined')
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def update_user_admin(request):
    user_id = request.data.get('id')
    if not user_id:
        return Response({"error": "User ID is required"}, status=400)
    
    user = get_object_or_404(User, id=user_id)
    
    # Update fields
    user.first_name = request.data.get('first_name', user.first_name)
    user.last_name = request.data.get('last_name', user.last_name)
    user.email = request.data.get('email', user.email)
    user.username = request.data.get('username', user.username)
    
    # Update project
    project_id = request.data.get('project_id')
    if project_id:
        try:
            project = Project.objects.get(id=project_id)
            user.primary_project = project
        except Project.DoesNotExist:
            pass
            
    # Update Permission Group — FIX #10: use `is None` not `== None`, handle 0 correctly
    # Frontend sends null to clear the group, or an integer ID to set it
    group_id = request.data.get('group_id', 'MISSING')
    if group_id != 'MISSING':
        if group_id is None:
            user.permission_group = None
        else:
            try:
                group = PermissionGroup.objects.get(id=group_id)
                user.permission_group = group
            except PermissionGroup.DoesNotExist:
                pass
            
    user.save()
    serializer = UserSerializer(user)
    return Response({"status": "success", "user": serializer.data})

@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_user_admin(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email', '')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    project_id = request.data.get('project_id')
    group_id = request.data.get('group_id')
    
    if not username or not password:
        return Response({"error": "Username and password are required"}, status=400)
    
    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists"}, status=400)
        
    try:
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
                user.primary_project = project
            except Project.DoesNotExist:
                pass
                
        if group_id:
            try:
                group = PermissionGroup.objects.get(id=group_id)
                user.permission_group = group
            except PermissionGroup.DoesNotExist:
                pass
                
        user.save()
        serializer = UserSerializer(user)
        return Response({"status": "success", "user": serializer.data}, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_user_admin(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    return Response({"status": "success"})

@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_permission_groups(request):
    from django.db.models import Count
    groups = PermissionGroup.objects.annotate(user_count=Count('users')).all()
    serializer = PermissionGroupSerializer(groups, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def update_permission_group(request):
    group_id = request.data.get('id')
    
    if group_id:
        group = get_object_or_404(PermissionGroup, id=group_id)
        serializer = PermissionGroupSerializer(group, data=request.data, partial=True)
    else:
        serializer = PermissionGroupSerializer(data=request.data)
        
    if serializer.is_valid():
        serializer.save()
        return Response({"status": "success", "group": serializer.data})
    
    return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_permission_group(request, group_id):
    group = get_object_or_404(PermissionGroup, id=group_id)
    group.delete()
    return Response({"status": "success"})
@api_view(['POST'])
@permission_classes([IsAdminUser])
def trigger_cleanup(request):
    try:
        days = request.data.get('days', 7)
        self_stdout = "" # To capture output if needed, but let's keep it simple
        call_command('cleanup_data', days=int(days))
        return Response({
            "status": "success", 
            "message": "Cleanup completed successfully. Database compacted."
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            "status": "error", 
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['POST'])
@rate_limit(requests=3, window=300, key_prefix='change_password')
def change_password_secure(request):
    try:
        current_password = request.data.get('currentPassword')
        new_password = request.data.get('newPassword')
        
        if not current_password or not new_password:
            return Response({
                "status": "error", 
                "message": "Missing required fields."
            }, status=status.HTTP_400_BAD_REQUEST)
            
        user = request.user
        
        # Verify current password
        if not user.check_password(current_password):
            return Response({
                "status": "error", 
                "message": "Incorrect current password."
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Update to new password
        user.set_password(new_password)
        user.save()
        
        return Response({
            "status": "success", 
            "message": "Password updated successfully."
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            "status": "error", 
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_dir_size(path='.'):
    total_size = 0
    try:
        if not os.path.exists(path):
            return 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
    except Exception:
        pass
    return total_size

def format_size(size_bytes):
    if size_bytes == 0: return "0 B"
    import math
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_system_usage(request):
    try:
        total_disk, used_disk, free_disk = shutil.disk_usage("/")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, 'db.sqlite3')
        media_path = os.path.join(base_dir, 'media')
        
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        media_size = get_dir_size(media_path)
        app_total_bytes = db_size + media_size
        
        return Response({
            "status": "success",
            "total_capacity": format_size(total_disk),
            "free_capacity": format_size(free_disk),
            "app_usage": format_size(app_total_bytes),
            "db_size": format_size(db_size),
            "media_size": format_size(media_size),
            "percentage": round((app_total_bytes / total_disk) * 100, 4) if total_disk > 0 else 0
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"status": "error", "message": str(e)}, status=500)
