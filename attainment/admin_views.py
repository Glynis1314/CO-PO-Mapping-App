"""
Admin (Principal) module views — CRUD for Academic Years, Departments,
Programs, Semesters, Courses.

All views enforce @login_required + @role_required('ADMIN').
Business rules are enforced server-side.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse

from django.contrib.auth.models import User
from django.utils import timezone

from attainment.models import (
    AcademicYear,
    Semester,
    SemesterType,
    Department,
    Program,
    Course,
    TeacherCourseAssignment,
    UserProfile,
    Role,
    GlobalConfig,
    GlobalConfigHistory,
    RolePermission,
)
from attainment.utils.rbac import role_required
from attainment.utils.audit import log_action


# ──────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────

def _sem_type(number):
    """Derive ODD/EVEN from semester number."""
    return SemesterType.ODD if number % 2 == 1 else SemesterType.EVEN


# ──────────────────────────────────────────────────────────────
#  ADMIN DASHBOARD (overview)
# ──────────────────────────────────────────────────────────────

@login_required
@role_required('ADMIN')
def admin_dashboard(request):
    active_ay = AcademicYear.objects.filter(is_active=True).first()
    context = {
        "ay_count": AcademicYear.objects.count(),
        "dept_count": Department.objects.count(),
        "program_count": Program.objects.count(),
        "semester_count": Semester.objects.count(),
        "course_count": Course.objects.count(),
        "active_ay": active_ay,
    }
    return render(request, "admin_panel/dashboard.html", context)


# ══════════════════════════════════════════════════════════════
#  A. ACADEMIC YEARS  (CRUD + activate)
# ══════════════════════════════════════════════════════════════

@login_required
@role_required('ADMIN')
def admin_academic_years(request):
    years = AcademicYear.objects.all().order_by("-is_active", "-name")
    return render(request, "admin_panel/academic_years.html", {"years": years})


@login_required
@role_required('ADMIN')
def admin_create_academic_year(request):
    if request.method != "POST":
        return redirect("admin_academic_years")

    name = request.POST.get("name", "").strip()

    if not name:
        messages.error(request, "Academic year name is required.")
        return redirect("admin_academic_years")

    if AcademicYear.objects.filter(name=name).exists():
        messages.error(request, f"Academic year '{name}' already exists.")
        return redirect("admin_academic_years")

    ay = AcademicYear.objects.create(name=name, is_active=False)
    log_action(request.user, "CREATE", "AcademicYear", ay.pk, f"Created {name}")
    messages.success(request, f"Academic year '{name}' created.")
    return redirect("admin_academic_years")


@login_required
@role_required('ADMIN')
def admin_activate_academic_year(request, ay_id):
    """Set this AY as active; deactivate all others."""
    if request.method != "POST":
        return redirect("admin_academic_years")

    ay = get_object_or_404(AcademicYear, pk=ay_id)
    with transaction.atomic():
        AcademicYear.objects.exclude(pk=ay_id).update(is_active=False)
        ay.is_active = True
        ay.save()

    log_action(request.user, "ACTIVATE", "AcademicYear", ay.pk, f"Activated {ay.name}")
    messages.success(request, f"'{ay.name}' is now the active academic year.")
    return redirect("admin_academic_years")


@login_required
@role_required('ADMIN')
def admin_delete_academic_year(request, ay_id):
    if request.method != "POST":
        return redirect("admin_academic_years")

    ay = get_object_or_404(AcademicYear, pk=ay_id)
    # Block if semesters exist under this AY
    if ay.semesters.exists():
        messages.error(request, f"Cannot delete '{ay.name}': it has semesters. Delete them first.")
        return redirect("admin_academic_years")

    name = ay.name
    ay.delete()
    log_action(request.user, "DELETE", "AcademicYear", ay_id, f"Deleted {name}")
    messages.success(request, f"Academic year '{name}' deleted.")
    return redirect("admin_academic_years")


# ══════════════════════════════════════════════════════════════
#  B. DEPARTMENTS  (CRUD + isFirstYear toggle)
# ══════════════════════════════════════════════════════════════

@login_required
@role_required('ADMIN')
def admin_departments(request):
    depts = Department.objects.annotate(
        program_count=Count("programs"),
        course_count=Count("courses"),
    ).order_by("-is_first_year", "name")
    return render(request, "admin_panel/departments.html", {"departments": depts})


@login_required
@role_required('ADMIN')
def admin_create_department(request):
    if request.method != "POST":
        return redirect("admin_departments")

    name = request.POST.get("name", "").strip()
    is_fy = request.POST.get("is_first_year") == "on"

    if not name:
        messages.error(request, "Department name is required.")
        return redirect("admin_departments")

    if Department.objects.filter(name=name).exists():
        messages.error(request, f"Department '{name}' already exists.")
        return redirect("admin_departments")

    # Only one department can be isFirstYear
    if is_fy and Department.objects.filter(is_first_year=True).exists():
        messages.error(request, "Another department is already marked as First Year. Unmark it first.")
        return redirect("admin_departments")

    dept = Department.objects.create(name=name, is_first_year=is_fy)
    log_action(request.user, "CREATE", "Department", dept.pk, f"Created {name}")
    messages.success(request, f"Department '{name}' created.")
    return redirect("admin_departments")


@login_required
@role_required('ADMIN')
def admin_edit_department(request, dept_id):
    if request.method != "POST":
        return redirect("admin_departments")

    dept = get_object_or_404(Department, pk=dept_id)
    name = request.POST.get("name", "").strip()
    is_fy = request.POST.get("is_first_year") == "on"

    if not name:
        messages.error(request, "Department name is required.")
        return redirect("admin_departments")

    # Unique check (exclude self)
    if Department.objects.filter(name=name).exclude(pk=dept_id).exists():
        messages.error(request, f"Department '{name}' already exists.")
        return redirect("admin_departments")

    # Only one FY
    if is_fy and Department.objects.filter(is_first_year=True).exclude(pk=dept_id).exists():
        messages.error(request, "Another department is already marked as First Year.")
        return redirect("admin_departments")

    dept.name = name
    dept.is_first_year = is_fy
    dept.save()
    log_action(request.user, "UPDATE", "Department", dept.pk, f"Updated {name}")
    messages.success(request, f"Department '{name}' updated.")
    return redirect("admin_departments")


@login_required
@role_required('ADMIN')
def admin_delete_department(request, dept_id):
    if request.method != "POST":
        return redirect("admin_departments")

    dept = get_object_or_404(Department, pk=dept_id)

    if dept.programs.exists():
        messages.error(request, f"Cannot delete '{dept.name}': it has programs.")
        return redirect("admin_departments")
    if dept.courses.exists():
        messages.error(request, f"Cannot delete '{dept.name}': it has courses.")
        return redirect("admin_departments")

    name = dept.name
    dept.delete()
    log_action(request.user, "DELETE", "Department", dept_id, f"Deleted {name}")
    messages.success(request, f"Department '{name}' deleted.")
    return redirect("admin_departments")


# ══════════════════════════════════════════════════════════════
#  C. PROGRAMS  (CRUD)
# ══════════════════════════════════════════════════════════════

@login_required
@role_required('ADMIN')
def admin_programs(request):
    programs = Program.objects.select_related("department").order_by("department__name", "name")
    departments = Department.objects.all().order_by("name")
    return render(request, "admin_panel/programs.html", {
        "programs": programs,
        "departments": departments,
    })


@login_required
@role_required('ADMIN')
def admin_create_program(request):
    if request.method != "POST":
        return redirect("admin_programs")

    name = request.POST.get("name", "").strip()
    dept_id = request.POST.get("department_id", "")

    if not name or not dept_id:
        messages.error(request, "Program name and department are required.")
        return redirect("admin_programs")

    dept = get_object_or_404(Department, pk=dept_id)

    if Program.objects.filter(name=name, department=dept).exists():
        messages.error(request, f"Program '{name}' already exists in {dept.name}.")
        return redirect("admin_programs")

    prog = Program.objects.create(name=name, department=dept)
    log_action(request.user, "CREATE", "Program", prog.pk, f"Created {name} under {dept.name}")
    messages.success(request, f"Program '{name}' created under {dept.name}.")
    return redirect("admin_programs")


@login_required
@role_required('ADMIN')
def admin_edit_program(request, prog_id):
    if request.method != "POST":
        return redirect("admin_programs")

    prog = get_object_or_404(Program, pk=prog_id)
    name = request.POST.get("name", "").strip()
    dept_id = request.POST.get("department_id", "")

    if not name or not dept_id:
        messages.error(request, "Program name and department are required.")
        return redirect("admin_programs")

    dept = get_object_or_404(Department, pk=dept_id)

    if Program.objects.filter(name=name, department=dept).exclude(pk=prog_id).exists():
        messages.error(request, f"Program '{name}' already exists in {dept.name}.")
        return redirect("admin_programs")

    prog.name = name
    prog.department = dept
    prog.save()
    log_action(request.user, "UPDATE", "Program", prog.pk, f"Updated {name}")
    messages.success(request, f"Program '{name}' updated.")
    return redirect("admin_programs")


@login_required
@role_required('ADMIN')
def admin_delete_program(request, prog_id):
    if request.method != "POST":
        return redirect("admin_programs")

    prog = get_object_or_404(Program, pk=prog_id)

    if prog.courses.exists():
        messages.error(request, f"Cannot delete '{prog.name}': it has courses.")
        return redirect("admin_programs")

    name = prog.name
    prog.delete()
    log_action(request.user, "DELETE", "Program", prog_id, f"Deleted {name}")
    messages.success(request, f"Program '{name}' deleted.")
    return redirect("admin_programs")


# ══════════════════════════════════════════════════════════════
#  D. SEMESTERS  (CRUD + lock/unlock)
# ══════════════════════════════════════════════════════════════

@login_required
@role_required('ADMIN')
def admin_semesters(request):
    selected_ay = request.GET.get("ay")
    academic_years = AcademicYear.objects.all().order_by("-is_active", "-name")

    semesters = Semester.objects.select_related("academic_year")
    if selected_ay:
        semesters = semesters.filter(academic_year_id=selected_ay)
    semesters = semesters.order_by("academic_year__name", "number")

    return render(request, "admin_panel/semesters.html", {
        "semesters": semesters,
        "academic_years": academic_years,
        "selected_ay": int(selected_ay) if selected_ay else None,
    })


@login_required
@role_required('ADMIN')
def admin_create_semester(request):
    if request.method != "POST":
        return redirect("admin_semesters")

    ay_id = request.POST.get("academic_year_id", "")
    number_str = request.POST.get("number", "")

    if not ay_id or not number_str:
        messages.error(request, "Academic year and semester number are required.")
        return redirect("admin_semesters")

    ay = get_object_or_404(AcademicYear, pk=ay_id)

    try:
        number = int(number_str)
        if number < 1 or number > 8:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, "Semester number must be between 1 and 8.")
        return redirect("admin_semesters")

    # Prevent duplicate semester under same AY
    if Semester.objects.filter(academic_year=ay, number=number).exists():
        messages.error(request, f"Semester {number} already exists for {ay.name}.")
        return redirect("admin_semesters")

    sem_type = _sem_type(number)
    sem = Semester.objects.create(
        academic_year=ay,
        number=number,
        type=sem_type,
    )
    log_action(request.user, "CREATE", "Semester", sem.pk,
               f"Created Sem {number} ({sem_type}) for {ay.name}")
    messages.success(request, f"Semester {number} ({sem_type}) created for {ay.name}.")
    return redirect("admin_semesters")


@login_required
@role_required('ADMIN')
def admin_toggle_semester_lock(request, sem_id):
    if request.method != "POST":
        return redirect("admin_semesters")

    sem = get_object_or_404(Semester, pk=sem_id)
    sem.is_locked = not sem.is_locked
    sem.save()

    status = "locked" if sem.is_locked else "unlocked"
    log_action(request.user, "TOGGLE_LOCK", "Semester", sem.pk,
               f"{status} Sem {sem.number} of {sem.academic_year.name}")
    messages.success(request, f"Semester {sem.number} ({sem.academic_year.name}) {status}.")
    return redirect("admin_semesters")


@login_required
@role_required('ADMIN')
def admin_delete_semester(request, sem_id):
    if request.method != "POST":
        return redirect("admin_semesters")

    sem = get_object_or_404(Semester, pk=sem_id)

    if sem.courses.exists():
        messages.error(request, f"Cannot delete Sem {sem.number}: it has courses.")
        return redirect("admin_semesters")

    label = f"Sem {sem.number} ({sem.academic_year.name})"
    sem.delete()
    log_action(request.user, "DELETE", "Semester", sem_id, f"Deleted {label}")
    messages.success(request, f"{label} deleted.")
    return redirect("admin_semesters")


# ══════════════════════════════════════════════════════════════
#  E. COURSES  (CRUD with filtering)
# ══════════════════════════════════════════════════════════════

@login_required
@role_required('ADMIN')
def admin_courses(request):
    # Filters
    f_ay = request.GET.get("ay")
    f_sem = request.GET.get("sem")
    f_dept = request.GET.get("dept")
    f_prog = request.GET.get("prog")

    courses = Course.objects.select_related(
        "semester", "semester__academic_year", "department", "program"
    )

    if f_ay:
        courses = courses.filter(semester__academic_year_id=f_ay)
    if f_sem:
        courses = courses.filter(semester_id=f_sem)
    if f_dept:
        courses = courses.filter(department_id=f_dept)
    if f_prog:
        courses = courses.filter(program_id=f_prog)

    courses = courses.order_by("code")

    academic_years = AcademicYear.objects.all().order_by("-is_active", "-name")
    semesters = Semester.objects.select_related("academic_year").order_by("academic_year__name", "number")
    departments = Department.objects.all().order_by("name")
    programs = Program.objects.select_related("department").order_by("department__name", "name")

    # For the selected AY, only show its semesters
    if f_ay:
        semesters = semesters.filter(academic_year_id=f_ay)

    # Available teachers (only TEACHER role and active) for assignment UI
    teachers = User.objects.filter(profile__role=Role.TEACHER, is_active=True).order_by('first_name', 'last_name', 'username')

    return render(request, "admin_panel/courses.html", {
        "courses": courses,
        "academic_years": academic_years,
        "semesters": semesters,
        "departments": departments,
        "programs": programs,
        "teachers": teachers,
        "f_ay": int(f_ay) if f_ay else None,
        "f_sem": int(f_sem) if f_sem else None,
        "f_dept": int(f_dept) if f_dept else None,
        "f_prog": int(f_prog) if f_prog else None,
    })


@login_required
@role_required('ADMIN')
def admin_create_course(request):
    if request.method != "POST":
        return redirect("admin_courses")

    code = request.POST.get("code", "").strip()
    name = request.POST.get("name", "").strip()
    sem_id = request.POST.get("semester_id", "")
    dept_id = request.POST.get("department_id", "")
    prog_id = request.POST.get("program_id", "")

    errors = []

    if not code:
        errors.append("Course code is required.")
    if not name:
        errors.append("Course name is required.")
    if not sem_id:
        errors.append("Semester is required.")
    if not dept_id:
        errors.append("Department is required.")
    if not prog_id:
        errors.append("Program is required.")

    if errors:
        for e in errors:
            messages.error(request, e)
        return redirect("admin_courses")

    sem = get_object_or_404(Semester, pk=sem_id)
    dept = get_object_or_404(Department, pk=dept_id)
    prog = get_object_or_404(Program, pk=prog_id)

    # Course code unique within the academic year
    if Course.objects.filter(
        code=code,
        semester__academic_year=sem.academic_year,
    ).exists():
        messages.error(request,
                       f"Course code '{code}' already exists in {sem.academic_year.name}.")
        return redirect("admin_courses")

    # Program must belong to the selected department
    if prog.department_id != dept.pk:
        messages.error(request,
                       f"Program '{prog.name}' does not belong to department '{dept.name}'.")
        return redirect("admin_courses")

    course = Course.objects.create(
        code=code,
        name=name,
        semester=sem,
        department=dept,
        program=prog,
        academic_year=sem.academic_year,
    )
    log_action(request.user, "CREATE", "Course", course.pk,
               f"Created {code} – {name}")
    messages.success(request, f"Course '{code} – {name}' created.")
    return redirect("admin_courses")


@login_required
@role_required('ADMIN')
def admin_edit_course(request, course_id):
    if request.method != "POST":
        return redirect("admin_courses")

    course = get_object_or_404(Course, pk=course_id)
    code = request.POST.get("code", "").strip()
    name = request.POST.get("name", "").strip()
    sem_id = request.POST.get("semester_id", "")
    dept_id = request.POST.get("department_id", "")
    prog_id = request.POST.get("program_id", "")

    if not code or not name or not sem_id or not dept_id or not prog_id:
        messages.error(request, "All fields are required.")
        return redirect("admin_courses")

    sem = get_object_or_404(Semester, pk=sem_id)
    dept = get_object_or_404(Department, pk=dept_id)
    prog = get_object_or_404(Program, pk=prog_id)

    # Code unique (exclude self)
    if Course.objects.filter(
        code=code,
        semester__academic_year=sem.academic_year,
    ).exclude(pk=course_id).exists():
        messages.error(request,
                       f"Course code '{code}' already exists in {sem.academic_year.name}.")
        return redirect("admin_courses")

    if prog.department_id != dept.pk:
        messages.error(request,
                       f"Program '{prog.name}' does not belong to department '{dept.name}'.")
        return redirect("admin_courses")

    course.code = code
    course.name = name
    course.semester = sem
    course.department = dept
    course.program = prog
    course.academic_year = sem.academic_year
    course.save()

    log_action(request.user, "UPDATE", "Course", course.pk, f"Updated {code}")
    messages.success(request, f"Course '{code}' updated.")
    return redirect("admin_courses")


@login_required
@role_required('ADMIN')
def admin_delete_course(request, course_id):
    if request.method != "POST":
        return redirect("admin_courses")

    course = get_object_or_404(Course, pk=course_id)

    if course.teachers.exists():
        messages.error(request, f"Cannot delete '{course.code}': teachers are assigned.")
        return redirect("admin_courses")
    if course.assessments.exists():
        messages.error(request, f"Cannot delete '{course.code}': assessments exist.")
        return redirect("admin_courses")

    code = course.code
    course.delete()
    log_action(request.user, "DELETE", "Course", course_id, f"Deleted {code}")
    messages.success(request, f"Course '{code}' deleted.")
    return redirect("admin_courses")


# ══════════════════════════════════════════════════════════════
#  F. USERS (Admin user management)
# ═════════════════════════════════════════════════════════════=

@login_required
@role_required('ADMIN')
def admin_users(request):
    """List users and show create/edit options."""
    users = User.objects.select_related('profile').order_by('-is_active', 'username')
    departments = Department.objects.all().order_by('name')
    roles = Role.choices
    return render(request, 'admin_panel/users.html', {
        'users': users,
        'departments': departments,
        'roles': roles,
    })


@login_required
@role_required('ADMIN')
def admin_create_user(request):
    if request.method != 'POST':
        return redirect('admin_users')

    full_name = request.POST.get('full_name', '').strip()
    email = request.POST.get('email', '').strip().lower()
    password = request.POST.get('password', '').strip()
    role = request.POST.get('role', '').strip()
    dept_id = request.POST.get('department_id', '')

    if not full_name or not email or not password or not role:
        messages.error(request, 'All fields (name, email, password, role) are required.')
        return redirect('admin_users')

    if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
        messages.error(request, 'A user with that email already exists.')
        return redirect('admin_users')

    dept = None
    if dept_id:
        dept = get_object_or_404(Department, pk=dept_id)

    parts = full_name.split()
    first_name = parts[0]
    last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

    user = User.objects.create_user(username=email, email=email, first_name=first_name, last_name=last_name)
    user.set_password(password)
    user.is_active = True
    user.save()

    profile = UserProfile.objects.create(user=user, role=role, department=dept)

    log_action(request.user, 'CREATE', 'User', user.pk, f'Created user {email} role={role}')
    messages.success(request, f'User "{email}" created.')
    return redirect('admin_users')


@login_required
@role_required('ADMIN')
def admin_edit_user(request, user_id):
    if request.method != 'POST':
        return redirect('admin_users')

    user = get_object_or_404(User, pk=user_id)
    profile = getattr(user, 'profile', None)
    if profile is None:
        profile = UserProfile.objects.create(user=user)

    full_name = request.POST.get('full_name', '').strip()
    email = request.POST.get('email', '').strip().lower()
    role = request.POST.get('role', '').strip()
    dept_id = request.POST.get('department_id', '')
    password = request.POST.get('password', '').strip()

    # Validate email uniqueness (exclude self)
    if email and User.objects.filter(email=email).exclude(pk=user_id).exists():
        messages.error(request, 'Another user with that email already exists.')
        return redirect('admin_users')

    if full_name:
        parts = full_name.split()
        user.first_name = parts[0]
        user.last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

    if email:
        user.email = email
        user.username = email

    if password:
        user.set_password(password)

    user.save()

    # Role & department
    if role:
        profile.role = role
    if dept_id:
        profile.department = get_object_or_404(Department, pk=dept_id)
    else:
        profile.department = None
    profile.save()

    log_action(request.user, 'UPDATE', 'User', user.pk, f'Updated user {user.username} role={profile.role}')
    messages.success(request, f'User "{user.username}" updated.')
    return redirect('admin_users')


@login_required
@role_required('ADMIN')
def admin_toggle_user_active(request, user_id):
    if request.method != 'POST':
        return redirect('admin_users')

    user = get_object_or_404(User, pk=user_id)
    if user.is_superuser:
        messages.error(request, 'Cannot deactivate a superuser.')
        return redirect('admin_users')

    profile = getattr(user, 'profile', None)
    user.is_active = not user.is_active
    user.save()

    if profile:
        profile.deleted_at = timezone.now() if not user.is_active else None
        profile.save()

    action = 'Deactivated' if not user.is_active else 'Reactivated'
    log_action(request.user, 'TOGGLE_ACTIVE', 'User', user.pk, f'{action} {user.username}')
    messages.success(request, f'User "{user.username}" {action.lower()}.')
    return redirect('admin_users')


# ══════════════════════════════════════════════════════════════
#  TEACHERS (Admin teacher-management + course assignments)
# ═════════════════════════════════════════════════════════════=

@login_required
@role_required('ADMIN')
def admin_teachers(request):
    """List teachers and allow course assignments."""
    teachers = User.objects.filter(profile__role=Role.TEACHER).select_related('profile').order_by('first_name', 'last_name', 'username')
    courses = Course.objects.select_related('department', 'semester', 'program').order_by('code')
    return render(request, 'admin_panel/teachers.html', {
        'teachers': teachers,
        'courses': courses,
    })


@login_required
@role_required('ADMIN')
def admin_assign_course(request):
    """Assign a course to a teacher (generic POST endpoint).
    Expects POST: teacher_id, course_id
    """
    if request.method != 'POST':
        return redirect('admin_teachers')

    teacher_id = request.POST.get('teacher_id')
    course_id = request.POST.get('course_id')

    if not teacher_id or not course_id:
        messages.error(request, 'Teacher and course are required.')
        return redirect('admin_teachers')

    teacher = get_object_or_404(User, pk=teacher_id)
    course = get_object_or_404(Course, pk=course_id)

    existing = TeacherCourseAssignment.objects.filter(course=course).first()
    if existing:
        if existing.teacher_id == teacher.id:
            messages.error(request, 'This teacher is already assigned to the course.')
        else:
            messages.error(request, f'Course {course.code} is already assigned to {existing.teacher.get_full_name() or existing.teacher.username}.')
        return redirect('admin_teachers')

    TeacherCourseAssignment.objects.create(teacher=teacher, course=course)
    log_action(request.user, 'ASSIGN', 'TeacherCourseAssignment', 0, f'Assigned {teacher.username} -> {course.code}')
    messages.success(request, f'Assigned {teacher.get_full_name() or teacher.username} to {course.code}.')
    return redirect('admin_teachers')


@login_required
@role_required('ADMIN')
def admin_unassign_course_from_teacher(request, teacher_id, course_id):
    if request.method != 'POST':
        return redirect('admin_teachers')

    assignment = TeacherCourseAssignment.objects.filter(teacher_id=teacher_id, course_id=course_id).first()
    if not assignment:
        messages.error(request, 'Assignment not found.')
        return redirect('admin_teachers')

    assignment.delete()
    log_action(request.user, 'UNASSIGN', 'TeacherCourseAssignment', 0, f'Removed teacher {teacher_id} from course {course_id}')
    messages.success(request, 'Assignment removed.')
    return redirect('admin_teachers')


# ══════════════════════════════════════════════════════════════
#  SETTINGS (Thresholds, Weightages & Change History)
# ═════════════════════════════════════════════════════════════=

@login_required
@role_required('ADMIN')
def admin_settings(request):
    """Show and update global attainment settings. Records a history entry on save."""
    cfg = GlobalConfig.objects.first()
    if cfg is None:
        cfg = GlobalConfig.objects.create()

    # Handle POST (save or reset)
    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'reset':
            # reset to defaults (use model defaults) — record per-field diffs so template can render them
            defaults = {
                'co_target_percent': 60.0,
                'co_target_marks_percent': 60.0,
                'direct_weightage': 0.8,
                'indirect_weightage': 0.2,
                'ia1_weightage': 0.2,
                'ia2_weightage': 0.2,
                'end_sem_weightage': 0.6,
                'po_target_level': 2.5,
                'level1_threshold': 50.0,
                'level2_threshold': 60.0,
                'level3_threshold': 70.0,
            }
            diffs = {}
            for k, dv in defaults.items():
                old = getattr(cfg, k)
                if float(old) != float(dv):
                    diffs[k] = [old, dv]
                    setattr(cfg, k, dv)

            cfg.save()
            version = GlobalConfigHistory.objects.filter(global_config=cfg).count() + 1
            if diffs:
                GlobalConfigHistory.objects.create(
                    global_config=cfg,
                    changed_by=request.user.username,
                    changes=diffs,
                    version=version,
                )
            else:
                # no-op reset (still record action)
                GlobalConfigHistory.objects.create(
                    global_config=cfg,
                    changed_by=request.user.username,
                    changes={'reset_to_defaults': ['no-change', 'defaults']},
                    version=version,
                )
            messages.success(request, 'Settings reset to defaults.')
            return redirect('admin_settings')

        # Save — validate weight sums
        try:
            new = {
                'co_target_percent': float(request.POST.get('co_target_percent', cfg.co_target_percent)),
                'co_target_marks_percent': float(request.POST.get('co_target_marks_percent', cfg.co_target_marks_percent)),
                'direct_weightage': float(request.POST.get('direct_weightage', cfg.direct_weightage)),
                'indirect_weightage': float(request.POST.get('indirect_weightage', cfg.indirect_weightage)),
                'ia1_weightage': float(request.POST.get('ia1_weightage', cfg.ia1_weightage)),
                'ia2_weightage': float(request.POST.get('ia2_weightage', cfg.ia2_weightage)),
                'end_sem_weightage': float(request.POST.get('end_sem_weightage', cfg.end_sem_weightage)),
                'po_target_level': float(request.POST.get('po_target_level', cfg.po_target_level)),
                'level1_threshold': float(request.POST.get('level1_threshold', cfg.level1_threshold)),
                'level2_threshold': float(request.POST.get('level2_threshold', cfg.level2_threshold)),
                'level3_threshold': float(request.POST.get('level3_threshold', cfg.level3_threshold)),
            }
        except ValueError:
            messages.error(request, 'Invalid numeric value provided.')
            return redirect('admin_settings')

        # Validate sums (IA1+IA2+EndSem == 1.0) and (direct+indirect == 1.0)
        if abs((new['ia1_weightage'] + new['ia2_weightage'] + new['end_sem_weightage']) - 1.0) > 0.001:
            messages.error(request, 'IA1 + IA2 + EndSem weightages must sum to 1.0')
            return redirect('admin_settings')
        if abs((new['direct_weightage'] + new['indirect_weightage']) - 1.0) > 0.001:
            messages.error(request, 'Direct + Indirect weightages must sum to 1.0')
            return redirect('admin_settings')

        # Compute diffs
        diffs = {}
        for k, v in new.items():
            old_v = getattr(cfg, k)
            if float(old_v) != float(v):
                diffs[k] = [old_v, v]
                setattr(cfg, k, v)

        if diffs:
            cfg.save()
            version = (GlobalConfigHistory.objects.filter(global_config=cfg).count() + 1)
            GlobalConfigHistory.objects.create(
                global_config=cfg,
                changed_by=request.user.username,
                changes=diffs,
                version=version,
            )
            log_action(request.user, 'UPDATE', 'GlobalConfig', cfg.pk, f'Updated config: {list(diffs.keys())}')
            messages.success(request, 'Settings saved.')
        else:
            messages.info(request, 'No changes detected.')

        return redirect('admin_settings')

    # GET — render page
    histories = GlobalConfigHistory.objects.filter(global_config=cfg).order_by('-version')[:50]
    context = {
        'config': cfg,
        'histories': histories,
    }
    return render(request, 'admin_panel/settings.html', context)


# ══════════════════════════════════════════════════════════════
#  RBAC / ROLES & PERMISSIONS
# ═════════════════════════════════════════════════════════════=


@login_required
@role_required('ADMIN')
def admin_rbac(request):
    # summary counts
    total = User.objects.count()
    admins = UserProfile.objects.filter(role=Role.ADMIN).count()
    hods = UserProfile.objects.filter(role=Role.HOD).count()
    teachers = UserProfile.objects.filter(role=Role.TEACHER).count()
    inactive = User.objects.filter(is_active=False).count()

    # Role overview — permissions per role (enabled)
    role_perms = {}
    # sensible default permission list to show in the matrix (keeps UI consistent)
    permissions_list = [
        'users.list','users.create','users.update','users.delete','users.changeRole','users.activate',
        'courses.create','courses.update','courses.delete','courses.view',
        'assessments.manage','marks.upload','marks.view','attainment.calculate','attainment.view',
        'reports.view','reports.generate','departments.manage','programs.manage','surveys.manage','cqi.create','cqi.review'
    ]

    role_perms_ordered = []
    for r_val, r_label in Role.choices:
        enabled = list(RolePermission.objects.filter(role=r_val, enabled=True).values_list('permission', flat=True))
        user_count = UserProfile.objects.filter(role=r_val).count()
        role_perms[r_val] = enabled
        role_perms_ordered.append((r_val, r_label, enabled, user_count))

    # Users list
    users = User.objects.select_related('profile').order_by('first_name', 'last_name')

    # permissions matrix (permission -> role -> bool)
    matrix = []
    for perm in permissions_list:
        row = {'permission': perm, 'roles': {}, 'values': []}
        for r_val, _ in Role.choices:
            exists = RolePermission.objects.filter(role=r_val, permission=perm, enabled=True).exists()
            row['roles'][r_val] = exists
            row['values'].append(exists)
        matrix.append(row)

    context = {
        'total': total,
        'admins': admins,
        'hods': hods,
        'teachers': teachers,
        'inactive': inactive,
        'role_perms': role_perms,
        'role_perms_ordered': role_perms_ordered,
        'users': users,
        'matrix': matrix,
        'roles': Role.choices,
    }
    return render(request, 'admin_panel/rbac.html', context)


@login_required
@role_required('ADMIN')
def admin_update_role_permissions(request, role):
    """Update the set of enabled permissions for a role (form POST)."""
    if request.method != 'POST':
        return redirect('admin_rbac')

    selected = request.POST.getlist('permissions')
    # ensure Role exists
    valid = [r for r, _ in Role.choices]
    if role not in valid:
        messages.error(request, 'Invalid role')
        return redirect('admin_rbac')

    # Set enabled=True for selected, False for others (for the known permission set)
    all_perms = set(request.POST.getlist('all_permissions'))
    for perm in all_perms:
        obj, created = RolePermission.objects.get_or_create(role=role, permission=perm)
        obj.enabled = perm in selected
        obj.save()

    log_action(request.user, 'UPDATE', 'RolePermission', role, f'Updated permissions for {role}')
    messages.success(request, f'Permissions updated for {role}.')
    return redirect('admin_rbac')


@login_required
@role_required('ADMIN')
def admin_toggle_permission(request):
    """AJAX/POST endpoint to toggle a single role-permission pair."""
    if request.method != 'POST':
        return redirect('admin_rbac')
    role = request.POST.get('role')
    perm = request.POST.get('permission')
    if not role or not perm:
        messages.error(request, 'Missing parameters')
        return redirect('admin_rbac')
    rp, _ = RolePermission.objects.get_or_create(role=role, permission=perm)
    rp.enabled = not rp.enabled
    rp.save()
    log_action(request.user, 'TOGGLE', 'RolePermission', role, f'{perm} -> {rp.enabled}')
    messages.success(request, 'Permission toggled.')
    return redirect('admin_rbac')

@login_required
@role_required('ADMIN')
def api_semesters_for_ay(request, ay_id):
    """Return semesters for a given academic year as JSON."""
    sems = Semester.objects.filter(academic_year_id=ay_id).order_by("number")
    data = [{"id": s.pk, "label": f"Sem {s.number} ({s.type})"} for s in sems]
    return JsonResponse(data, safe=False)


@login_required
@role_required('ADMIN')
def api_programs_for_dept(request, dept_id):
    """Return programs for a given department as JSON."""
    progs = Program.objects.filter(department_id=dept_id).order_by("name")
    data = [{"id": p.pk, "name": p.name} for p in progs]
    return JsonResponse(data, safe=False)
