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

from attainment.models import (
    AcademicYear,
    Semester,
    SemesterType,
    Department,
    Program,
    Course,
    TeacherCourseAssignment,
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

    return render(request, "admin_panel/courses.html", {
        "courses": courses,
        "academic_years": academic_years,
        "semesters": semesters,
        "departments": departments,
        "programs": programs,
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
#  API HELPERS (JSON for cascading dropdowns)
# ══════════════════════════════════════════════════════════════

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
