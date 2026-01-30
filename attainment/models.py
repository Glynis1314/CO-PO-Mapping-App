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


class Semester(models.Model):
    """
    Represents an Odd/Even semester within an Academic Year.
    Example: ODD, EVEN
    """
    SEMESTER_CHOICES = [
        ("ODD", "Odd"),
        ("EVEN", "Even"),
    ]
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    kind = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("academic_year", "kind")

    def __str__(self):
        return f"{self.academic_year.name} {self.kind}"


class Program(models.Model):
    """
    Example:
    B.Tech Computer Science
    B.Tech Information Technology
    """
    name = models.CharField(max_length=200, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Course(models.Model):
    """
    A subject/course offered in a specific academic year and semester
    """
    code = models.CharField(max_length=20)   # e.g., 18CSC205J
    name = models.CharField(max_length=200)  # e.g., Operating Systems
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, blank=True)
    is_first_year_course = models.BooleanField(default=False)

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
    BLOOM_LEVELS = [
        (1, "Remember"),
        (2, "Understand"),
        (3, "Apply"),
        (4, "Analyze"),
        (5, "Evaluate"),
        (6, "Create"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    code = models.CharField(max_length=10)  # CO1, CO2, ...
    description = models.TextField()
    bloom_level = models.IntegerField(choices=BLOOM_LEVELS, default=2)

    # Attainment configuration
    # The system-wide CO target (percent of students) is in GlobalConfig.co_target_percentage (60%)
    # But keep a course-level override trace if needed (readonly by teachers)
    expected_proficiency = models.FloatField(default=60.0, help_text="percent of marks per student to be considered meeting the CO (e.g., 60%)")

    def __str__(self):
        return f"{self.course.code} - {self.code}"

    class Meta:
        unique_together = ("course", "code")



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
    IA-1, IA-2, End-Semester, and other assessments.

    `assessment_category` is used by the global weightage configuration (IA-1 = 20%, IA-2 = 20%, End-Semester = 60%).
    """
    ASSESSMENT_TYPES = [
        ("CIA", "CIA"),
        ("QUIZ", "Quiz"),
        ("LAB", "Lab"),
        ("PROJECT", "Project"),
        ("SEE", "SEE"),
    ]

    ASSESSMENT_CATEGORIES = [
        ("IA1", "IA-1"),
        ("IA2", "IA-2"),
        ("END", "End-Semester"),
        ("OTHER", "Other"),
    ]

    name = models.CharField(max_length=50)  # CIA 1, CIA 2, etc.
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES)
    assessment_category = models.CharField(max_length=10, choices=ASSESSMENT_CATEGORIES, default="OTHER")
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    max_marks = models.FloatField()

    def __str__(self):
        return f"{self.course.code} - {self.name} ({self.assessment_category})"

class AssessmentComponent(models.Model):
    """
    Questions / Rubric criteria within an assessment
    """
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    component_number = models.CharField(max_length=20)  # Q1, Q2, C1, etc.
    max_marks = models.FloatField()

    # Mapping component to a CO (mandatory)
    course_outcome = models.ForeignKey(CourseOutcome, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("assessment", "component_number")

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


# ============================================================
# GOVERNANCE, SURVEYS, UPLOADS, CQI, AND AUDIT LOGS
# ============================================================

class UserProfile(models.Model):
    """Extends the default User with a role and optional department/program assignment."""
    ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        ("HOD", "HOD"),
        ("TEACHER", "Teacher"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class GlobalConfig(models.Model):
    """Central configuration controlled by Admin (singleton-like)."""
    name = models.CharField(max_length=50, unique=True, default="DEFAULT")

    # CO Target (percentage of students meeting threshold)
    co_target_percentage = models.FloatField(default=60.0, help_text="Percent of students")
    # The per-student threshold to be considered 'met' (i.e. 60% of CO marks)
    co_student_threshold_percent = models.FloatField(default=60.0)

    # Attainment level thresholds are stored as JSON to allow auditing
    # Example: {"3": 60, "2": 50, "1": 40, "0": 0}
    attainment_thresholds = models.JSONField(default=dict)

    # Assessment weightages (percent)
    ia1_weight = models.FloatField(default=20.0)
    ia2_weight = models.FloatField(default=20.0)
    end_sem_weight = models.FloatField(default=60.0)

    direct_weight = models.FloatField(default=0.8)
    indirect_weight = models.FloatField(default=0.2)

    po_target_value = models.FloatField(default=2.5)

    # Allow automatic creation of Student records during marks import
    allow_student_auto_create = models.BooleanField(default=True, help_text="If True, unknown RollNos will create Student rows on import")

    locked = models.BooleanField(default=True, help_text="When True only Admin can change the record")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"GlobalConfig ({self.name})"


class MarksUpload(models.Model):
    """Tracks CSV/Excel uploads of marks for an Assessment."""
    STATUS = [("PENDING", "Pending"), ("VALIDATED", "Validated"), ("FAILED", "Failed"), ("IMPORTED", "Imported")]

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to="marks_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    error_report = models.TextField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True, help_text="Validation summary, columns, question ids, etc.")

    def __str__(self):
        return f"MarksUpload ({self.assessment}) by {self.uploaded_by.username} - {self.status}"


class SurveyTemplate(models.Model):
    """Defines the official template for Exit Surveys (course/program)."""
    SURVEY_TYPE = [("COURSE", "Course Exit"), ("PROGRAM", "Program Exit")]
    name = models.CharField(max_length=200)
    survey_type = models.CharField(max_length=10, choices=SURVEY_TYPE)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # For course surveys we expect one question per CO; for program surveys one per PO
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.survey_type})"


class SurveyQuestion(models.Model):
    """A question inside a survey template mapped to a CO or PO code (like CO1 or PO3)."""
    template = models.ForeignKey(SurveyTemplate, on_delete=models.CASCADE, related_name="questions")
    code = models.CharField(max_length=10)  # CO1, CO2, PO1 etc.
    text = models.TextField()

    class Meta:
        unique_together = ("template", "code")

    def __str__(self):
        return f"{self.template.name} - {self.code}"


class SurveyUpload(models.Model):
    """Stores uploaded survey CSV and a compact parsed summary for auditing."""
    template = models.ForeignKey(SurveyTemplate, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to="survey_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_locked = models.BooleanField(default=True, help_text="Survey responses are read-only after upload")
    total_responses = models.IntegerField(default=0)
    # summary could store counts per response option per question: {"CO1": {"Strongly Agree": 10, ...}, ...}
    summary = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"SurveyUpload ({self.template.name}) by {self.uploaded_by.username} - {self.uploaded_at}"


class COIndirectAttainment(models.Model):
    """Indirect attainment derived from course exit survey per CO."""
    course_outcome = models.ForeignKey(CourseOutcome, on_delete=models.CASCADE)
    survey_upload = models.ForeignKey(SurveyUpload, on_delete=models.CASCADE)
    indirect_score = models.FloatField(help_text="Average score per student (0-3 scale)")
    total_responses = models.IntegerField()

    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course_outcome", "survey_upload")

    def __str__(self):
        return f"Indirect - {self.course_outcome} - {self.indirect_score}"


class COFinalAttainment(models.Model):
    """Stores direct, indirect and final CO attainment values and level."""
    course_outcome = models.OneToOneField(CourseOutcome, on_delete=models.CASCADE)
    direct_percentage = models.FloatField()
    indirect_score = models.FloatField()
    final_value = models.FloatField(help_text="Weighted final CO value (0-100 or 0-3 depending on chosen scale)")

    attainment_level = models.IntegerField(choices=[(0,"Not Attained"),(1,"Low"),(2,"Moderate"),(3,"High")])
    computed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Final - {self.course_outcome} - {self.final_value} ({self.attainment_level})"


class CoursePOAttainment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    program_outcome = models.ForeignKey(ProgramOutcome, on_delete=models.CASCADE)
    value = models.FloatField()
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "program_outcome")

    def __str__(self):
        return f"{self.course} - {self.program_outcome} = {self.value}"


class ProgramPOAttainment(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    program_outcome = models.ForeignKey(ProgramOutcome, on_delete=models.CASCADE)
    value = models.FloatField()
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("program", "program_outcome")

    def __str__(self):
        return f"{self.program} - {self.program_outcome} = {self.value}"


class CQIAction(models.Model):
    """Action taken / CQI by teacher when a CO is below target."""
    STATUS = [("OPEN","Open"),("IN_PROGRESS","In Progress"),("CLOSED","Closed")]
    course_outcome = models.ForeignKey(CourseOutcome, on_delete=models.CASCADE)
    raised_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="actions_raised")
    description = models.TextField()
    raised_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, choices=STATUS, default="OPEN")
    hod_reviewed = models.BooleanField(default=False)
    hod_remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"CQI - {self.course_outcome} ({self.status})"


class AuditLog(models.Model):
    """Auditable log for critical system actions."""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=200)
    object_type = models.CharField(max_length=100, null=True, blank=True)
    object_id = models.CharField(max_length=200, null=True, blank=True)
    details = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"


class SemesterLock(models.Model):
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    locked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    locked_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ("semester",)

    def __str__(self):
        return f"Locked {self.semester} by {self.locked_by} at {self.locked_at}"
