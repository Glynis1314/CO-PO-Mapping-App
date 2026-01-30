from django.core.management.base import BaseCommand
from attainment.models import GlobalConfig, ProgramOutcome, Department, Program

class Command(BaseCommand):
    help = 'Seed initial configuration: GlobalConfig and PO1..PO12 and First Year Department'

    def handle(self, *args, **options):
        cfg, created = GlobalConfig.objects.get_or_create(name='DEFAULT')
        if created:
            cfg.co_target_percentage = 60.0
            cfg.co_student_threshold_percent = 60.0
            cfg.attainment_thresholds = {"3": 60, "2": 50, "1": 40, "0": 0}
            cfg.ia1_weight = 20.0
            cfg.ia2_weight = 20.0
            cfg.end_sem_weight = 60.0
            cfg.direct_weight = 0.8
            cfg.indirect_weight = 0.2
            cfg.po_target_value = 2.5
            cfg.locked = True
            cfg.save()
            self.stdout.write(self.style.SUCCESS('Created GlobalConfig DEFAULT'))
        else:
            self.stdout.write(self.style.NOTICE('GlobalConfig DEFAULT already exists'))

        for i in range(1, 13):
            code = f"PO{i}"
            po, ok = ProgramOutcome.objects.get_or_create(code=code, defaults={"description": f"Program Outcome {code}"})
            if ok:
                self.stdout.write(self.style.SUCCESS(f'Created {code}'))

        dept, dcreated = Department.objects.get_or_create(name='First Year')
        if dcreated:
            self.stdout.write(self.style.SUCCESS('Created Department: First Year'))

        # Create a generic First Year Program if not exists
        p, pcreated = Program.objects.get_or_create(name='First Year Common', defaults={ 'department': dept })
        if pcreated:
            self.stdout.write(self.style.SUCCESS('Created Program: First Year Common'))

        self.stdout.write(self.style.SUCCESS('Seeding completed.'))