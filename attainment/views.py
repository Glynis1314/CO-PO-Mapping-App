import csv
from django.shortcuts import render, redirect
from .models import Student, Assessment, AssessmentComponent, StudentMark, CourseOutcome, COAttainment, Department, POAttainment, Course, TeacherCourseAssignment
from .models import AcademicYear,COtoPOMapping, ProgramOutcome
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.db.models import Sum
from .models import GlobalConfig, COSurveyAggregate
from django.db import models


def dashboard_hod(request):

    context = {
        "year_count": AcademicYear.objects.count(),
        "course_count": Course.objects.count(),
        "teacher_count": TeacherCourseAssignment.objects.values('teacher').distinct().count(),
        "low_co_count": COAttainment.objects.filter(attainment_level__lt=2).count(),
    }

    return render(request, "dashboard_hod.html", context)



def dashboard_principal(request):
    return principal_dashboard(request)

def upload_marks(request, assessment_id):

    assessment = Assessment.objects.get(id=assessment_id)

    if request.method == "POST" and request.FILES.get('csv_file'):

        csv_file = request.FILES['csv_file']
        decoded = csv_file.read().decode("utf-8").splitlines()
        reader = csv.DictReader(decoded)

        # wipe previous marks for this assessment
        StudentMark.objects.filter(component__assessment=assessment).delete()

        for row in reader:

            roll = row["RollNumber"]

            student, _ = Student.objects.get_or_create(
                roll_number=roll,
                defaults={"name": roll, "department_id": 1}
            )

            for key, value in row.items():

                if key == "RollNumber":
                    continue

                component = AssessmentComponent.objects.filter(
                    assessment=assessment,
                    component_number=key
                ).first()

                if component:

                    StudentMark.objects.create(
                        student=student,
                        component=component,
                        question=component,
                        marks=float(value or 0),
                        marks_obtained=float(value or 0)
                    )

        calculate_co_attainment(assessment.id)
        return redirect("attainment_report")

    return render(request, "upload_marks.html")


from .models import GlobalConfig, COSurveyAggregate


from django.db.models import Sum

from django.db.models import Sum
from .models import GlobalConfig, COSurveyAggregate


from django.db.models import Sum

def calculate_co_attainment(assessment_id):

    assessment = Assessment.objects.get(id=assessment_id)
    course = assessment.course
    config = GlobalConfig.objects.first()

    outcomes = CourseOutcome.objects.filter(course=course)

    # students who actually have marks FOR THIS assessment
    students = StudentMark.objects.filter(
        component__assessment=assessment
    ).values_list('student_id', flat=True).distinct()

    print("Students found:", len(students))

    for co in outcomes:

        components = AssessmentComponent.objects.filter(
            course_outcome=co,
            assessment=assessment
        )

        total_max = components.aggregate(Sum('max_marks'))['max_marks__sum'] or 0

        print(co.code, "max marks:", total_max)

        if total_max == 0:
            continue

        passed = 0

        for sid in students:

            obtained = StudentMark.objects.filter(
                student_id=sid,
                component__in=components
            ).aggregate(Sum('marks_obtained'))['marks_obtained__sum'] or 0

            percent = (obtained / total_max) * 100

            if percent >= co.expected_proficiency:
                passed += 1

        total_students = len(students)

        if total_students == 0:
            continue

        attainment_percent = (passed / total_students) * 100

        if attainment_percent >= config.level3_threshold:
            level = "LEVEL_3"
        elif attainment_percent >= config.level2_threshold:
            level = "LEVEL_2"
        elif attainment_percent >= config.level1_threshold:
            level = "LEVEL_1"
        else:
            level = "LEVEL_0"

        direct = attainment_percent

        survey = COSurveyAggregate.objects.filter(course_outcome=co).first()
        indirect = (survey.average_score / 5) * 100 if survey else 0

        final = (
            direct * config.direct_weightage +
            indirect * config.indirect_weightage
        )

        COAttainment.objects.update_or_create(
            course_outcome=co,
            defaults={
                "attainment_percentage": round(attainment_percent, 2),
                "direct_score": round(direct, 2),
                "indirect_score": round(indirect, 2),
                "final_score": round(final, 2),
                "level": level,
                "attainment_level": int(level.split("_")[1])
            }
        )

    calculate_po_attainment(course)


def calculate_po_attainment(course):

    config = GlobalConfig.objects.first()
    pos = ProgramOutcome.objects.all()

    for po in pos:

        mappings = COtoPOMapping.objects.filter(
            program_outcome=po,
            course_outcome__course=course
        )

        weighted_sum = 0
        total_weight = 0

        for mapping in mappings:

            co_att = COAttainment.objects.filter(
                course_outcome=mapping.course_outcome
            ).first()

            if not co_att:
                continue

            weighted_sum += (co_att.final_score or 0) * mapping.level
            total_weight += mapping.level

        if total_weight == 0:
            continue

        direct = weighted_sum / total_weight
        indirect = 0  # Add PO survey later if needed

        final = (
            direct * config.direct_weightage +
            indirect * config.indirect_weightage
        )

        # Level mapping
        if final >= config.level3_threshold:
            level = 3
        elif final >= config.level2_threshold:
            level = 2
        elif final >= config.level1_threshold:
            level = 1
        else:
            level = 0

        POAttainment.objects.update_or_create(
            program_outcome=po,
            defaults={
                "direct_score": round(direct, 2),
                "indirect_score": indirect,
                "final_score": round(final, 2),
                "attainment_level": level,
                "attainment_percentage": round(final, 2),
            }
        )
   


def academic_years_list(request):
    # This renders the table with existing data
    years = AcademicYear.objects.all()
    return render(request, 'academic_years.html', {'years': years})

def create_academic_year(request):
    if request.method == "POST":
        year_range = request.POST.get('name')
        semester = request.POST.get('semester')
        full_name = f"{year_range} {semester}"
        
        # Check if this exact academic cycle already exists
        if AcademicYear.objects.filter(name=full_name).exists():
            # Using Django messages to alert the user
            messages.error(request, f"The academic year '{full_name}' already exists!")
            return redirect('academic_years_list')
        
        # If it's unique, save it to the database [cite: 535-536]
        AcademicYear.objects.create(name=full_name)
        messages.success(request, f"Successfully created {full_name}.")
        
        return redirect('academic_years_list')
    
def assign_subjects_view(request):
    """Renders the assignment page with existing data."""
    context = {
        'courses': Course.objects.all(),
        'teachers': User.objects.filter(is_staff=False), # Only show teachers, not admins
        'assignments': TeacherCourseAssignment.objects.all(),
    }
    return render(request, 'assign_subjects.html', context)

def assign_subject_action(request):
    """Handles the POST request to save a new assignment."""
    if request.method == "POST":
        course_id = request.POST.get('course_id')
        teacher_id = request.POST.get('teacher_id')
        
        # Prevent duplicate assignments
        if TeacherCourseAssignment.objects.filter(course_id=course_id, teacher_id=teacher_id).exists():
            messages.warning(request, "This teacher is already assigned to this subject.")
        else:
            TeacherCourseAssignment.objects.create(
                course_id=course_id, 
                teacher_id=teacher_id
            )
            messages.success(request, "Subject assigned successfully!")
            
    return redirect('assign_subjects')

@login_required
def teacher_dashboard(request):
    # Fetch only the subjects assigned to the logged-in teacher
    assigned_courses = TeacherCourseAssignment.objects.filter(teacher=request.user)
    
    # We can also fetch the CO status for these courses for a quick overview
    # This helps show "Completion Status" on the dashboard
    context = {
        'assignments': assigned_courses,
        'user_name': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'teacher/dashboard.html', context)


def index_view(request):
    return render(request, "index.html")


# The logic for Principal dashboard
def principal_dashboard(request):
    # --- Real Summary Stats ---
    # Count total departments in the system 
    total_depts = Department.objects.count()
    
    # Count all assessments created by teachers across all courses [cite: 59, 244]
    total_assessments = Assessment.objects.count()
    
    # Count COs where attainment level is 0 or 1 (Below Threshold) [cite: 410, 715]
    low_cos_count = COAttainment.objects.filter(attainment_level__lt=2).count()

    # --- Department Table Data ---
    departments = Department.objects.all()
    dept_stats = []

    for dept in departments:
        # Calculate Average CO Attainment for this department [cite: 1076, 1079]
        avg_co = COAttainment.objects.filter(
            course_outcome__course__department=dept
        ).aggregate(Avg('attainment_percentage'))['attainment_percentage__avg'] or 0

        # Calculate Average PO Attainment for this department [cite: 1076, 1083]
        avg_po = POAttainment.objects.filter(
           program_outcome__program__department=dept
        ).aggregate(
            Avg('attainment_percentage')
        )['attainment_percentage__avg'] or 0

        # Determine the "Gap" Label based on the average % [cite: 72, 264, 1105]
        if avg_co >= 70:
            gap_label, gap_class = "Low", "success"
        elif avg_co >= 60:
            gap_label, gap_class = "Moderate", "warning"
        else:
            gap_label, gap_class = "High", "danger"

        dept_stats.append({
            'name': dept.name,
            'avg_co': round(avg_co, 1),
            'avg_po': round(avg_po, 1),
            'gap_label': gap_label,
            'gap_class': gap_class
        })

    context = {
        'total_depts': total_depts,
        'total_assessments': total_assessments,
        'low_cos_count': low_cos_count,
        'dept_stats': dept_stats
    }
    return render(request, 'dashboard_principal.html', context)


def attainment_report_view(request):
    # Fetch all years and subjects for the dropdowns
    academic_years = AcademicYear.objects.all()
    subjects = Course.objects.all()
    
    # Initialize variables for the report
    selected_year = request.GET.get('academic_year')
    selected_subject = request.GET.get('subject')
    co_results = []
    po_results = []

    if selected_year and selected_subject:
        co_results = COAttainment.objects.filter(
            course_outcome__course_id=selected_subject,
            academic_year_id=selected_year
        )

        po_results = POAttainment.objects.filter(
            academic_year_id=selected_year,
            course_id=selected_subject
    )


    context = {
        'academic_years': academic_years,
        'subjects': subjects,
        'co_results': co_results,
        'po_results': po_results,
        'selected_year': selected_year,
        'selected_subject': selected_subject,
    }
    return render(request, 'reports/attainment_report.html', context)


def gap_analysis_view(request):

    departments = Department.objects.all()
    gap_rows = []

    for dept in departments:
        avg_co = COAttainment.objects.filter(
            course_outcome__course__department=dept
        ).aggregate(Avg('attainment_percentage'))['attainment_percentage__avg'] or 0

        if avg_co >= 70:
            label, css = "Low", "success"
        elif avg_co >= 60:
            label, css = "Moderate", "warning"
        else:
            label, css = "High", "danger"

        gap_rows.append({
            "department": dept.name,
            "avg": round(avg_co, 1),
            "label": label,
            "css": css
        })

    return render(request, "reports/gap_analysis.html", {
        "rows": gap_rows
    })
