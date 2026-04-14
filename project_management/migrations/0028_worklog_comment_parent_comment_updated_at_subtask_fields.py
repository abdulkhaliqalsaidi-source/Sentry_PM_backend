from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('project_management', '0027_pluginmodel_automationrule_automationcondition_and_more'),
    ]

    operations = [
        # 1. Add time_estimate to Task
        migrations.AddField(
            model_name='task',
            name='time_estimate',
            field=models.FloatField(default=0.0, help_text='Estimated time in hours'),
        ),

        # 2. Add parent (threading) and updated_at to Comment
        migrations.AddField(
            model_name='comment',
            name='parent',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='replies',
                to='project_management.comment',
            ),
        ),
        migrations.AddField(
            model_name='comment',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),

        # 3. Upgrade Subtask model
        migrations.AddField(
            model_name='subtask',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='subtask',
            name='assigned_to',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_subtasks',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='subtask',
            name='priority',
            field=models.CharField(
                choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')],
                default='MEDIUM',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='subtask',
            name='status',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='subtasks',
                to='project_management.taskstatus',
            ),
        ),
        migrations.AddField(
            model_name='subtask',
            name='due_date',
            field=models.DateField(blank=True, null=True),
        ),

        # 4. Create WorkLog model
        migrations.CreateModel(
            name='WorkLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hours', models.FloatField(help_text='Hours logged')),
                ('description', models.CharField(blank=True, max_length=255)),
                ('logged_at', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('task', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='work_logs',
                    to='project_management.task',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='work_logs',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-logged_at']},
        ),
    ]
