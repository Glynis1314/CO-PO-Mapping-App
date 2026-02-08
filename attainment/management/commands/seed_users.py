"""
Management command: creates test users for each role.

Usage:
    python manage.py seed_users

Creates these accounts (if they don't already exist):

    Username        Password        Role
    ─────────       ─────────       ─────
    admin           admin123        ADMIN (Principal)
    hod             hod123          HOD
    teacher1        teacher123      TEACHER
    teacher2        teacher123      TEACHER
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from attainment.models import UserProfile, Department, Role


USERS = [
    {"username": "admin",    "password": "admin123",   "role": Role.ADMIN,
     "first_name": "Admin",  "last_name": "Principal", "email": "admin@dbit.in"},
    {"username": "hod",      "password": "hod123",     "role": Role.HOD,
     "first_name": "HOD",    "last_name": "CompEngg",  "email": "hod@dbit.in"},
    {"username": "teacher1", "password": "teacher123", "role": Role.TEACHER,
     "first_name": "Teacher", "last_name": "One",      "email": "t1@dbit.in"},
    {"username": "teacher2", "password": "teacher123", "role": Role.TEACHER,
     "first_name": "Teacher", "last_name": "Two",      "email": "t2@dbit.in"},
]


class Command(BaseCommand):
    help = "Create test users with UserProfile roles (admin, hod, teacher1, teacher2)"

    def handle(self, *args, **options):
        dept = Department.objects.first()  # assign first dept to all

        for u in USERS:
            user, created = User.objects.get_or_create(
                username=u["username"],
                defaults={
                    "first_name": u["first_name"],
                    "last_name": u["last_name"],
                    "email": u["email"],
                    "is_staff": u["role"] in (Role.ADMIN, Role.HOD),
                },
            )
            if created:
                user.set_password(u["password"])
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f"  Created user: {u['username']} / {u['password']}"
                ))
            else:
                self.stdout.write(f"  User {u['username']} already exists — skipped")

            # Create or update UserProfile
            profile, p_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={"role": u["role"], "department": dept},
            )
            if not p_created:
                profile.role = u["role"]
                profile.department = dept
                profile.save()

            self.stdout.write(f"    -> role={profile.role}, dept={dept}")

        self.stdout.write(self.style.SUCCESS("\nDone. You can now log in with these accounts."))
