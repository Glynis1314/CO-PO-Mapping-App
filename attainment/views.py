import csv
from django.shortcuts import render, redirect
from .models import Student, AssessmentComponent, StudentMark, CourseOutcome, COAttainment
from django.shortcuts import redirect
from .models import AcademicYear
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Course, TeacherCourseAssignment
from django.contrib.auth.decorators import login_required


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