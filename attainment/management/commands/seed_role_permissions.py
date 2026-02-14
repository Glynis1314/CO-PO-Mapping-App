from django.core.management.base import BaseCommand
from attainment.models import RolePermission, Role


class Command(BaseCommand):
    help = 'Seed RolePermission table with the standard Admin/HOD/Teacher permissions mapping.'

    PERMISSIONS = [
        'users.list','users.create','users.update','users.delete','users.changeRole','users.activate',
        'courses.create','courses.update','courses.delete','courses.view',
        'assessments.manage','marks.upload','marks.view','attainment.calculate','attainment.view',
        'reports.view','reports.generate','departments.manage','programs.manage','surveys.manage','cqi.create','cqi.review'
    ]

    MAPPING = {
        'ADMIN': PERMISSIONS,  # full access
        'HOD': [
            'users.list',
            'courses.view','courses.create','courses.update',
            'assessments.manage','marks.upload','marks.view',
            'attainment.calculate','attainment.view',
            'reports.view','reports.generate',
            'cqi.create','cqi.review',
            'surveys.manage','programs.manage'
        ],
        'TEACHER': [
            'courses.view',
            'assessments.manage',
            'marks.upload','marks.view',
            'attainment.view',
            'reports.view',
            'cqi.create'
        ],
    }

    def handle(self, *args, **options):
        all_perms = set(self.PERMISSIONS)
        created = 0
        updated = 0
        for role, perms in self.MAPPING.items():
            perms_set = set(perms)
            for perm in all_perms:
                enabled = perm in perms_set
                obj, was_created = RolePermission.objects.update_or_create(
                    role=role, permission=perm,
                    defaults={'enabled': enabled}
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f'RolePermission seed complete — created: {created}, updated: {updated}'))
