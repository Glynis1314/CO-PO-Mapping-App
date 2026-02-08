from django.contrib import admin
from .models import (
    UserProfile,
    RolePermission,
    AcademicYear,
    Semester,
    Department,
    Program,
    Course,
    TeacherCourseAssignment,
    ProgramOutcome,
    CourseOutcome,
    COtoPOMapping,
    Assessment,
    AssessmentComponent,
    Student,
    MarksUpload,
    StudentMark,
    COAttainment,
    COSurveyAggregate,
    CourseSurveyUpload,
    CQIAction,
    POAttainment,
    ProgramSurveyUpload,
    POSurveyAggregate,
    SurveyTemplate,
    GlobalConfig,
    GlobalConfigHistory,
    UserSession,
    AuditLog,
    EvidenceFile,
)

# User & Permissions
admin.site.register(UserProfile)
admin.site.register(RolePermission)

# Academic Structure
admin.site.register(AcademicYear)
admin.site.register(Semester)
admin.site.register(Department)
admin.site.register(Program)
admin.site.register(Course)
admin.site.register(TeacherCourseAssignment)

# Outcomes & Mappings
admin.site.register(ProgramOutcome)
admin.site.register(CourseOutcome)
admin.site.register(COtoPOMapping)

# Assessments & Marks
admin.site.register(Assessment)
admin.site.register(AssessmentComponent)
admin.site.register(Student)
admin.site.register(MarksUpload)
admin.site.register(StudentMark)

# Attainment
admin.site.register(COAttainment)
admin.site.register(COSurveyAggregate)
admin.site.register(CourseSurveyUpload)
admin.site.register(CQIAction)
admin.site.register(POAttainment)
admin.site.register(ProgramSurveyUpload)
admin.site.register(POSurveyAggregate)

# Survey, Config, Sessions, Audit
admin.site.register(SurveyTemplate)
admin.site.register(GlobalConfig)
admin.site.register(GlobalConfigHistory)
admin.site.register(UserSession)
admin.site.register(AuditLog)

# Evidence
admin.site.register(EvidenceFile)
