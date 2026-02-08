from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ============================================================
# ENUMS  (matching Prisma enums)
# ============================================================

class Role(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    HOD = "HOD", "HOD"
    TEACHER = "TEACHER", "Teacher"


class SemesterType(models.TextChoices):
    ODD = "ODD", "Odd"
    EVEN = "EVEN", "Even"


class AssessmentType(models.TextChoices):
    IA1 = "IA1", "IA 1"
    IA2 = "IA2", "IA 2"
    ENDSEM = "ENDSEM", "End Semester"
    # Legacy types kept so existing rows are valid
    CIA = "CIA", "CIA"
    QUIZ = "QUIZ", "Quiz"
    LAB = "LAB", "Lab"
    PROJECT = "PROJECT", "Project"
    SEE = "SEE", "SEE"


class AttainmentLevel(models.TextChoices):
    LEVEL_0 = "LEVEL_0", "Level 0"
    LEVEL_1 = "LEVEL_1", "Level 1"
    LEVEL_2 = "LEVEL_2", "Level 2"
    LEVEL_3 = "LEVEL_3", "Level 3"


class SurveyOption(models.TextChoices):
    STRONGLY_AGREE = "STRONGLY_AGREE", "Strongly Agree"
    AGREE = "AGREE", "Agree"
    NEUTRAL = "NEUTRAL", "Neutral"
    DISAGREE = "DISAGREE", "Disagree"


class CqiStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    REVIEWED = "REVIEWED", "Reviewed"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"


class SurveyType(models.TextChoices):
    COURSE = "COURSE", "Course"
    PROGRAM = "PROGRAM", "Program"


# ============================================================
# USER PROFILE  (extends Django's built-in User)
# ============================================================

class UserProfile(models.Model):
    """
    Extra fields from Prisma User that Django's auth.User lacks.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.TEACHER)
    department = models.ForeignKey(
        "Department", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="user_profiles"
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class RolePermission(models.Model):
    """
    Prisma: RolePermission – per-role permission flags.
    """
    role = models.CharField(max_length=10, choices=Role.choices)
    permission = models.CharField(max_length=100)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("role", "permission")]
        indexes = [models.Index(fields=["role"])]

    def __str__(self):
        return f"{self.role} – {self.permission}"


# ============================================================
# ACADEMIC STRUCTURE
# ============================================================

class AcademicYear(models.Model):
    name = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Semester(models.Model):
    """
    Prisma: Semester – sits between AcademicYear and Course.
    """
    number = models.IntegerField()
    type = models.CharField(max_length=4, choices=SemesterType.choices)
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="semesters"
    )
    is_locked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.academic_year.name} – Sem {self.number} ({self.type})"


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_first_year = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Program(models.Model):
    """
    Prisma: Program – degree programme under a department.
    """
    name = models.CharField(max_length=200)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="programs"
    )

    def __str__(self):
        return self.name


class Course(models.Model):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="courses"
    )
    # Legacy FK kept so existing rows are valid
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, null=True, blank=True
    )
    # New Prisma FKs (nullable for existing data)
    semester = models.ForeignKey(
        Semester, on_delete=models.CASCADE,
        null=True, blank=True, related_name="courses"
    )
    program = models.ForeignKey(
        Program, on_delete=models.CASCADE,
        null=True, blank=True, related_name="courses"
    )

    def __str__(self):
        return f"{self.code} - {self.name}"


class TeacherCourseAssignment(models.Model):
    """
    Prisma: CourseTeacher
    """
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="teaching"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="teachers"
    )

    def __str__(self):
        return f"{self.teacher.username} → {self.course.code}"


# ============================================================
# PROGRAM & COURSE OUTCOMES
# ============================================================

class ProgramOutcome(models.Model):
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField()
    program = models.ForeignKey(
        Program, on_delete=models.CASCADE,
        null=True, blank=True, related_name="outcomes"
    )

    def __str__(self):
        return self.code


class CourseOutcome(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="outcomes"
    )
    code = models.CharField(max_length=10)
    description = models.TextField()
    bloom_levels = models.JSONField(default=list, blank=True)

    # Legacy attainment-config fields (still useful)
    expected_proficiency = models.FloatField(default=60.0)
    attainment_target = models.FloatField(default=70.0)

    def __str__(self):
        return f"{self.course.code} - {self.code}"


class COtoPOMapping(models.Model):
    """
    Prisma: CoPoMapping – articulation matrix cell.
    """
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        null=True, blank=True, related_name="co_po_mappings"
    )
    course_outcome = models.ForeignKey(
        CourseOutcome, on_delete=models.CASCADE, related_name="co_po_mappings"
    )
    program_outcome = models.ForeignKey(
        ProgramOutcome, on_delete=models.CASCADE, related_name="co_po_mappings"
    )
    # `value` in Prisma, kept as `level` for backward compat
    level = models.IntegerField(
        choices=[(1, "Low"), (2, "Moderate"), (3, "High")]
    )

    class Meta:
        unique_together = [("course_outcome", "program_outcome")]

    def __str__(self):
        return f"{self.course_outcome.code} → {self.program_outcome.code}"


# ============================================================
# ASSESSMENTS
# ============================================================

class Assessment(models.Model):
    name = models.CharField(max_length=50)
    assessment_type = models.CharField(
        max_length=20, choices=AssessmentType.choices
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="assessments"
    )
    max_marks = models.FloatField()
    total_marks = models.IntegerField(null=True, blank=True)
    date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.course.code} - {self.name}"


class AssessmentComponent(models.Model):
    """
    Prisma: AssessmentQuestion – a question/rubric criterion within an assessment.
    """
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="questions"
    )
    component_number = models.CharField(max_length=20)  # questionCode
    max_marks = models.FloatField()
    course_outcome = models.ForeignKey(
        CourseOutcome, on_delete=models.CASCADE, related_name="questions"
    )

    def __str__(self):
        return f"{self.assessment.name} - {self.component_number}"


# ============================================================
# STUDENTS & MARKS
# ============================================================

class Student(models.Model):
    roll_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.roll_number} - {self.name}"


class MarksUpload(models.Model):
    """
    Prisma: MarksUpload – tracks each CSV/Excel upload.
    """
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="marks_uploads"
    )
    file_name = models.CharField(max_length=255)
    uploaded_by = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    record_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.file_name} ({self.record_count} rows)"


class StudentMark(models.Model):
    # Legacy FKs (kept for existing data)
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, null=True, blank=True
    )
    component = models.ForeignKey(
        AssessmentComponent, on_delete=models.CASCADE, null=True, blank=True,
        related_name="student_marks"
    )
    marks_obtained = models.FloatField(null=True, blank=True)

    # Prisma fields
    roll_no = models.CharField(max_length=50, blank=True, default="")
    marks = models.FloatField(null=True, blank=True)
    question = models.ForeignKey(
        AssessmentComponent, on_delete=models.CASCADE,
        null=True, blank=True, related_name="marks"
    )
    marks_upload = models.ForeignKey(
        MarksUpload, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="student_marks"
    )

    def __str__(self):
        roll = self.roll_no or (self.student.roll_number if self.student else "?")
        return f"{roll} – {self.marks or self.marks_obtained}"


# ============================================================
# ATTAINMENT
# ============================================================

class COAttainment(models.Model):
    course_outcome = models.OneToOneField(
        CourseOutcome, on_delete=models.CASCADE, related_name="attainment"
    )
    # Legacy fields kept
    attainment_percentage = models.FloatField(null=True, blank=True)
    attainment_level = models.IntegerField(
        choices=[(0, "Not Attained"), (1, "Low"), (2, "Moderate"), (3, "High")],
        null=True, blank=True,
    )
    # Prisma fields
    ia1_level = models.FloatField(null=True, blank=True)
    ia2_level = models.FloatField(null=True, blank=True)
    end_sem_level = models.FloatField(null=True, blank=True)
    direct_score = models.FloatField(null=True, blank=True)
    indirect_score = models.FloatField(null=True, blank=True)
    final_score = models.FloatField(null=True, blank=True)
    level = models.CharField(
        max_length=10, choices=AttainmentLevel.choices,
        null=True, blank=True,
    )
    calculated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.course_outcome.code} – {self.level or self.attainment_level}"


class COSurveyAggregate(models.Model):
    """
    Prisma: COSurveyAggregate – indirect attainment per CO.
    """
    course_outcome = models.OneToOneField(
        CourseOutcome, on_delete=models.CASCADE, related_name="survey"
    )
    responses = models.IntegerField(default=0)
    average_score = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.course_outcome.code} survey avg {self.average_score}"


class CourseSurveyUpload(models.Model):
    """
    Prisma: CourseSurveyUpload
    """
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="survey_uploads"
    )
    file_name = models.CharField(max_length=255)
    uploaded_by = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    record_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.course.code} survey – {self.file_name}"


class CQIAction(models.Model):
    """
    Prisma: CQIAction – continuous quality improvement.
    """
    course_outcome = models.ForeignKey(
        CourseOutcome, on_delete=models.CASCADE, related_name="cqi_actions"
    )
    action_taken = models.TextField()
    remarks = models.TextField(null=True, blank=True)
    created_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10, choices=CqiStatus.choices, default=CqiStatus.PENDING
    )
    reviewed_by = models.CharField(max_length=255, null=True, blank=True)
    review_notes = models.TextField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"CQI {self.course_outcome.code} – {self.status}"


class POAttainment(models.Model):
    program_outcome = models.OneToOneField(
        ProgramOutcome, on_delete=models.CASCADE, related_name="attainment"
    )
    # Legacy fields kept
    attainment_percentage = models.FloatField(null=True, blank=True)
    attainment_level = models.IntegerField(
        choices=[(0, "Not Attained"), (1, "Low"), (2, "Moderate"), (3, "High")],
        null=True, blank=True,
    )
    # Prisma fields
    direct_score = models.FloatField(null=True, blank=True)
    indirect_score = models.FloatField(null=True, blank=True)
    final_score = models.FloatField(null=True, blank=True)
    calculated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.program_outcome.code} – {self.final_score or self.attainment_level}"


class ProgramSurveyUpload(models.Model):
    """
    Prisma: ProgramSurveyUpload
    """
    program_id = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255)
    uploaded_by = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    record_count = models.IntegerField(default=0)

    def __str__(self):
        return f"Program survey – {self.file_name}"


class POSurveyAggregate(models.Model):
    """
    Prisma: POSurveyAggregate
    """
    program_outcome = models.OneToOneField(
        ProgramOutcome, on_delete=models.CASCADE, related_name="survey"
    )
    responses = models.IntegerField(default=0)
    average_score = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.program_outcome.code} survey avg {self.average_score}"


# ============================================================
# SURVEY TEMPLATES
# ============================================================

class SurveyTemplate(models.Model):
    type = models.CharField(max_length=10, choices=SurveyType.choices)
    entity_id = models.CharField(max_length=255, null=True, blank=True)
    template = models.JSONField(default=dict)
    created_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Survey tpl ({self.type}) – {self.entity_id}"


# ============================================================
# GLOBAL CONFIG
# ============================================================

class GlobalConfig(models.Model):
    co_target_percent = models.FloatField(default=60.0)
    co_target_marks_percent = models.FloatField(default=60.0)
    direct_weightage = models.FloatField(default=0.8)
    indirect_weightage = models.FloatField(default=0.2)
    ia1_weightage = models.FloatField(default=0.2)
    ia2_weightage = models.FloatField(default=0.2)
    end_sem_weightage = models.FloatField(default=0.6)
    po_target_level = models.FloatField(default=2.5)
    level3_threshold = models.FloatField(default=70.0)
    level2_threshold = models.FloatField(default=60.0)
    level1_threshold = models.FloatField(default=50.0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"GlobalConfig #{self.pk}"


class GlobalConfigHistory(models.Model):
    global_config = models.ForeignKey(
        GlobalConfig, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="histories"
    )
    changed_by = models.CharField(max_length=255)
    changes = models.JSONField(default=dict)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Config v{self.version} by {self.changed_by}"


# ============================================================
# SESSION (API token sessions, separate from Django sessions)
# ============================================================

class UserSession(models.Model):
    """
    Prisma: Session – token-based sessions.
    """
    token = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="api_sessions"
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.user.username}"


# ============================================================
# AUDIT LOG
# ============================================================

class AuditLog(models.Model):
    action = models.CharField(max_length=100)
    entity = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=255)
    user_id = models.CharField(max_length=255)
    details = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} {self.entity}#{self.entity_id}"


# ============================================================
# EVIDENCE STORAGE  (kept from original)
# ============================================================

class EvidenceFile(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to="evidence/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidence - {self.course.code}"
