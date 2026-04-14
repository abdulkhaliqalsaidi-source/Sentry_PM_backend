from django.db import migrations


def seed_kpis(apps, schema_editor):
    KPI = apps.get_model('project_management', 'KPI')

    default_kpis = [
        # ── AUTOMATED ─────────────────────────────────────────────────
        {
            'name': 'Completion Rate',
            'description': 'Percentage of assigned tasks completed during the evaluation period.',
            'type': 'AUTOMATED',
            'weight': 2.0,
            'is_active': True,
        },
        {
            'name': 'On-time Delivery',
            'description': 'Percentage of completed tasks finished before the period end date.',
            'type': 'AUTOMATED',
            'weight': 2.0,
            'is_active': True,
        },
        {
            'name': 'Lead Time',
            'description': 'Average time (in hours) from task creation to completion. Lower is better.',
            'type': 'AUTOMATED',
            'weight': 1.5,
            'is_active': True,
        },
        {
            'name': 'Bug Rate',
            'description': 'Inverse of the percentage of bug-type tasks relative to total tasks.',
            'type': 'AUTOMATED',
            'weight': 1.5,
            'is_active': True,
        },
        # ── MANUAL ────────────────────────────────────────────────────
        {
            'name': 'Communication',
            'description': 'Quality of communication and collaboration with the team.',
            'type': 'MANUAL',
            'weight': 1.0,
            'is_active': True,
        },
        {
            'name': 'Code Quality',
            'description': 'Code review scores, adherence to standards and best practices.',
            'type': 'MANUAL',
            'weight': 1.0,
            'is_active': True,
        },
    ]

    for kpi_data in default_kpis:
        KPI.objects.get_or_create(name=kpi_data['name'], defaults=kpi_data)


def remove_kpis(apps, schema_editor):
    KPI = apps.get_model('project_management', 'KPI')
    names = ['Completion Rate', 'On-time Delivery', 'Lead Time', 'Bug Rate', 'Communication', 'Code Quality']
    KPI.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('project_management', '0025_kpi_evaluationperiod_userevaluation_evaluationdetail'),
    ]

    operations = [
        migrations.RunPython(seed_kpis, remove_kpis),
    ]
