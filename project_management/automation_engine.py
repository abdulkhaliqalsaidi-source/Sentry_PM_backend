import logging
from .models import AutomationRule, Task, TaskStatus, Label, Comment, Notification

logger = logging.getLogger(__name__)


class AutomationEngine:

    @staticmethod
    def process_event(event_type, project_id, task=None, **kwargs):
        """Entry point — find matching rules and execute them."""
        if not task or not project_id:
            return
        try:
            rules = AutomationRule.objects.filter(
                project_id=project_id,
                active=True,
                triggers__trigger_type=event_type
            ).distinct()

            for rule in rules:
                if AutomationEngine.evaluate_conditions(rule, task):
                    AutomationEngine.execute_actions(rule, task)
        except Exception as e:
            logger.error(f"AutomationEngine.process_event error: {e}")

    @staticmethod
    def evaluate_conditions(rule, task):
        """Return True if all conditions pass (AND logic)."""
        conditions = rule.conditions.all()
        if not conditions.exists():
            return True

        for condition in conditions:
            # Support nested fields like "status.name", "status.category"
            attrs = condition.field.split('.')
            field_val = task
            for attr in attrs:
                field_val = getattr(field_val, attr, None)
                if field_val is None:
                    break

            val_str = str(field_val).strip() if field_val is not None else ""
            cond_val = condition.value.strip()

            if condition.operator == 'EQUALS':
                if val_str.lower() != cond_val.lower():
                    return False
            elif condition.operator == 'NOT_EQUALS':
                if val_str.lower() == cond_val.lower():
                    return False
            elif condition.operator == 'CONTAINS':
                if cond_val.lower() not in val_str.lower():
                    return False
            elif condition.operator == 'GREATER_THAN':
                try:
                    if float(val_str) <= float(cond_val):
                        return False
                except (ValueError, TypeError):
                    return False
            elif condition.operator == 'LESS_THAN':
                try:
                    if float(val_str) >= float(cond_val):
                        return False
                except (ValueError, TypeError):
                    return False

        return True

    @staticmethod
    def execute_actions(rule, task):
        """Execute all actions for a matched rule."""
        actions = rule.actions.all()
        changed = False

        for action in actions:
            try:
                params = action.parameters or {}

                # ── SET_STATUS ──────────────────────────────────────
                if action.action_type == 'SET_STATUS':
                    status_id = params.get('status_id')
                    status_name = params.get('status_name')

                    new_status = None
                    if status_id:
                        new_status = TaskStatus.objects.filter(
                            id=status_id, project=task.project
                        ).first()
                    elif status_name:
                        new_status = TaskStatus.objects.filter(
                            name__iexact=status_name, project=task.project
                        ).first()

                    if new_status and task.status_id != new_status.id:
                        task.status = new_status
                        changed = True
                        logger.info(f"[Automation] SET_STATUS → {new_status.name} on task {task.id}")

                # ── ASSIGN_USER ─────────────────────────────────────
                elif action.action_type == 'ASSIGN_USER':
                    from tracker.models import User
                    user_id = params.get('user_id')
                    username = params.get('username')

                    user = None
                    if user_id:
                        user = User.objects.filter(id=user_id).first()
                    elif username:
                        user = User.objects.filter(username=username).first()

                    if user and task.assigned_to_id != user.id:
                        task.assigned_to = user
                        changed = True
                        logger.info(f"[Automation] ASSIGN_USER → {user.username} on task {task.id}")

                # ── ADD_LABEL ───────────────────────────────────────
                elif action.action_type == 'ADD_LABEL':
                    label_id = params.get('label_id')
                    label_name = params.get('label_name')

                    label = None
                    if label_id:
                        label = Label.objects.filter(id=label_id).first()
                    elif label_name:
                        label = Label.objects.filter(
                            name__iexact=label_name, project=task.project
                        ).first()

                    if label and not task.labels.filter(id=label.id).exists():
                        task.labels.add(label)
                        logger.info(f"[Automation] ADD_LABEL → {label.name} on task {task.id}")

                # ── ADD_COMMENT ─────────────────────────────────────
                elif action.action_type == 'ADD_COMMENT':
                    content = params.get('content', '').strip()
                    if content:
                        Comment.objects.create(
                            task=task,
                            author=task.project.owner,  # system comment from project owner
                            content=f"🤖 **Automation:** {content}"
                        )
                        logger.info(f"[Automation] ADD_COMMENT on task {task.id}")

                # ── SEND_NOTIFICATION ───────────────────────────────
                elif action.action_type == 'SEND_NOTIFICATION':
                    from tracker.models import User
                    recipient_id = params.get('user_id')
                    recipient_username = params.get('username')
                    message = params.get('message', 'Automated notification')

                    recipient = None
                    if recipient_id:
                        recipient = User.objects.filter(id=recipient_id).first()
                    elif recipient_username:
                        recipient = User.objects.filter(username=recipient_username).first()
                    elif task.assigned_to:
                        recipient = task.assigned_to

                    if recipient:
                        Notification.objects.create(
                            recipient=recipient,
                            actor=task.project.owner,
                            verb=message,
                            type='SYSTEM',
                            task=task,
                            project=task.project
                        )
                        logger.info(f"[Automation] SEND_NOTIFICATION → {recipient.username}")

            except Exception as e:
                logger.error(f"[Automation] Error executing action '{action.action_type}' on task {task.id}: {e}")

        # Save task once after all field changes
        if changed:
            try:
                task.save(update_fields=['status', 'assigned_to'])
            except Exception as e:
                logger.error(f"[Automation] Failed to save task {task.id}: {e}")
