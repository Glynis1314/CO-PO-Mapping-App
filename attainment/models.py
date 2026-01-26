from django.db import models
from django.contrib.auth.models import User

# ============================================================
# ACADEMIC STRUCTURE
# ============================================================

class AcademicYear(models.Model):
    """
    Example:
    2025-26 ODD
    2025-26 EVEN
    """
    name = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Department(models.Model):
    """
    Example:
    Computer Engineering
    Information Technology
    """
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    """
    A subject/course offered in a specific academic year
    """
    code = models.CharField(max_length=20)   # e.g., 18CSC205J
    name = models.CharField(max_length=200)  # e.g., Operating Systems
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.code} - {self.name}"


class TeacherCourseAssignment(models.Model):
    """
    HOD assigns courses to teachers
    """
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.teacher.username} → {self.course.code}"


# ============================================================
# PROGRAM & COURSE OUTCOMES
# ============================================================

class ProgramOutcome(models.Model):
    """
    NBA Program Outcomes (PO1 – PO12)
    """
    code = models.CharField(max_length=10, unique=True)  # PO1, PO2, ...
    description = models.TextField()

    def __str__(self):
        return self.code


class CourseOutcome(models.Model):
    """
    Course Outcomes defined per course
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    code = models.CharField(max_length=10)  # CO1, CO2, ...
    description = models.TextField()

    # Attainment configuration (Method B)
    expected_proficiency = models.FloatField(default=60.0)  # p%
    attainment_target = models.FloatField(default=70.0)     # y%

    def __str__(self):
        return f"{self.course.code} - {self.code}"


class COtoPOMapping(models.Model):
    """
    Articulation matrix: CO → PO mapping
    """
    course_outcome = models.ForeignKey(CourseOutcome, on_delete=models.CASCADE)
    program_outcome = models.ForeignKey(ProgramOutcome, on_delete=models.CASCADE)
    level = models.IntegerField(
        choices=[
            (1, "Low"),
            (2, "Moderate"),
            (3, "High")
        ]
    )

    def __str__(self):
        return f"{self.course_outcome.code} → {self.program_outcome.code}"


# ============================================================
# ASSESSMENTS
# ============================================================

class Assessment(models.Model):
    """
    CIA / Quiz / Lab / Project etc.
    """
    ASSESSMENT_TYPES = [
        ("CIA", "CIA"),
        ("QUIZ", "Quiz"),
        ("LAB", "Lab"),
        ("PROJECT", "Project"),
        ("SEE", "SEE"),
    ]

    name = models.CharField(max_length=50)  # CIA 1, CIA 2, etc.
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    max_marks = models.FloatField()

    def __str__(self):
        return f"{self.course.code} - {self.name}"


class AssessmentComponent(models.Model):
    """
    Questions / Rubric criteria within an assessment
    """
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    component_number = models.CharField(max_length=20)  # Q1, Q2, C1, etc.
    max_marks = models.FloatField()

    # Mapping component to a CO
    course_outcome = models.ForeignKey(CourseOutcome, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.assessment.name} - {self.component_number}"


# ============================================================
# STUDENTS & MARKS
# ============================================================

class Student(models.Model):
    """
    Students enrolled in a course
    """
    roll_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.roll_number} - {self.name}"


class StudentMark(models.Model):
    """
    Marks obtained by a student for an assessment component
    (manual entry or CSV upload)
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    component = models.ForeignKey(AssessmentComponent, on_delete=models.CASCADE)
    marks_obtained = models.FloatField()

    def __str__(self):
        return f"{self.student.roll_number} - {self.component}"


# ============================================================
# ATTAINMENT RESULTS (DIRECT – METHOD B)
# ============================================================

class COAttainment(models.Model):
    """
    Computed CO attainment (Direct method – Method B)
    """
    course_outcome = models.ForeignKey(CourseOutcome, on_delete=models.CASCADE)
    attainment_percentage = models.FloatField()
    attainment_level = models.IntegerField(
        choices=[
            (0, "Not Attained"),
            (1, "Low"),
            (2, "Moderate"),
            (3, "High"),
        ]
    )

    def __str__(self):
        return f"{self.course_outcome.code} - Level {self.attainment_level}"


class POAttainment(models.Model):
    """
    Final PO attainment derived from CO attainment
    """
    program_outcome = models.ForeignKey(ProgramOutcome, on_delete=models.CASCADE)
    attainment_percentage = models.FloatField()
    attainment_level = models.IntegerField(
        choices=[
            (0, "Not Attained"),
            (1, "Low"),
            (2, "Moderate"),
            (3, "High"),
        ]
    )

    def __str__(self):
        return f"{self.program_outcome.code} - Level {self.attainment_level}"


# ============================================================
# EVIDENCE STORAGE
# ============================================================

class EvidenceFile(models.Model):
    """
    Files uploaded for NBA / NAAC audits
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to="evidence/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidence - {self.course.code}"
