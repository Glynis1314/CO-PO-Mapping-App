# Generated migration: add unique constraint to TeacherCourseAssignment.course
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attainment", "0003_auditlog_globalconfig_programsurveyupload_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="teachercourseassignment",
            constraint=models.UniqueConstraint(fields=["course"], name="unique_course_assignment"),
        ),
    ]
