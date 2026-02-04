import csv
from django.shortcuts import render, redirect
from .models import Student, Assessment, AssessmentComponent, StudentMark, CourseOutcome, COAttainment, Department, POAttainment, Course, TeacherCourseAssignment
from .models import AcademicYear
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count


def dashboard_hod(request):
    return render(request, "dashboard_hod.html")


def dashboard_principal(request):
    return principal_dashboard(request)


def upload_marks(request, assessment_id):
    if request.method == "POST" and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)

        for row in reader:
            # 1. Get or Create Student
            student, _ = Student.objects.get_or_create(
                roll_number=row['RollNumber'],
                defaults={'name': row['Name'], 'department_id': 1} # Adjust dept logic as needed
            )

            # 2. Loop through columns to find Question Marks
            for key, value in row.items():
                if key not in ['RollNumber', 'Name']:
                    # Match column header (e.g., 'Q1') to AssessmentComponent
                    component = AssessmentComponent.objects.filter(
                        assessment_id=assessment_id, 
                        component_number=key
                    ).first()
                    
                    if component:
                        StudentMark.objects.update_or_create(
                            student=student,
                            component=component,
                            defaults={'marks_obtained': float(value)}
                        )
        
        # 3. After upload, trigger the CO Attainment calculation
        calculate_co_attainment(assessment_id)
        return redirect('attainment_report')

    return render(request, 'upload_marks.html')

def calculate_co_attainment(assessment_id):
    """
    Implements Method B: % of students scoring >= p% marks [cite: 48-50, 234].
    """
    outcomes = CourseOutcome.objects.all() # In production, filter by course
    for co in outcomes:
        components = AssessmentComponent.objects.filter(course_outcome=co)
        total_students = Student.objects.count()
        students_passed = 0

        for student in Student.objects.all():
            # Calculate student's performance for this CO
            marks = StudentMark.objects.filter(student=student, component__in=components)
            # Logic: Did they get >= p% of total possible marks for this CO? [cite: 51, 157, 235]
            # ... calculation logic ...
            
        # 4. Map average % to Levels 1, 2, or 3 based on targets (x, y, z) [cite: 52-54, 236-239, 715]
        


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
            program_outcome__course__department=dept
        ).aggregate(Avg('attainment_percentage'))['attainment_percentage__avg'] or 0

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
    return render(request, 'principal/dashboard.html', context)


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
