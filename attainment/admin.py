from django.contrib import admin
from .models import (
    AcademicYear,
    Department,
    Semester,
    Program,
    Course,
    TeacherCourseAssignment,
    ProgramOutcome,
    CourseOutcome,
    COtoPOMapping,
    Assessment,
    AssessmentComponent,
    Student,
    StudentMark,
    COAttainment,
    COFinalAttainment,
    COIndirectAttainment,
    POAttainment,
    CoursePOAttainment,
    ProgramPOAttainment,
    EvidenceFile,
    UserProfile,
    GlobalConfig,
    MarksUpload,
    SurveyTemplate,
    SurveyQuestion,
    SurveyUpload,
    CQIAction,
    AuditLog,
    SemesterLock,
)

admin.site.register(AcademicYear)
admin.site.register(Department)
admin.site.register(Semester)
admin.site.register(Program)
admin.site.register(Course)
admin.site.register(TeacherCourseAssignment)

admin.site.register(ProgramOutcome)
admin.site.register(CourseOutcome)
admin.site.register(COtoPOMapping)

admin.site.register(Assessment)
admin.site.register(AssessmentComponent)

admin.site.register(Student)
admin.site.register(StudentMark)

admin.site.register(COAttainment)
admin.site.register(COFinalAttainment)
admin.site.register(COIndirectAttainment)
admin.site.register(POAttainment)
admin.site.register(CoursePOAttainment)
admin.site.register(ProgramPOAttainment)

admin.site.register(EvidenceFile)
admin.site.register(UserProfile)
admin.site.register(GlobalConfig)
admin.site.register(MarksUpload)
admin.site.register(SurveyTemplate)
admin.site.register(SurveyQuestion)
admin.site.register(SurveyUpload)
admin.site.register(CQIAction)
admin.site.register(AuditLog)
admin.site.register(SemesterLock)
