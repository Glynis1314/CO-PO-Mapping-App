from django.contrib import admin
from .models import (
    AcademicYear,
    Department,
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
    POAttainment,
    EvidenceFile,
)

admin.site.register(AcademicYear)
admin.site.register(Department)
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
admin.site.register(POAttainment)

admin.site.register(EvidenceFile)
