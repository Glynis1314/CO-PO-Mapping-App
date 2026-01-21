from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [

    # -------------------------
    # Landing / Dashboards
    # -------------------------
    path('', TemplateView.as_view(template_name="index.html"), name="index"),

    path('hod/dashboard/',
         TemplateView.as_view(template_name="dashboard_hod.html"),
         name="dashboard_hod"),

    path('teacher/dashboard/',
         TemplateView.as_view(template_name="dashboard_teacher.html"),
         name="dashboard_teacher"),

    path('principal/dashboard/',
         TemplateView.as_view(template_name="dashboard_principal.html"),
         name="dashboard_principal"),

    # -------------------------
    # HOD pages
    # -------------------------
    path('subjects/',
         TemplateView.as_view(template_name="subjects.html"),
         name="subjects"),

    path('assign-subjects/',
         TemplateView.as_view(template_name="assign_subjects.html"),
         name="assign_subjects"),

    path('academic-years/',
         TemplateView.as_view(template_name="academic_years.html"),
         name="academic_years"),

    path('settings/users/',
         TemplateView.as_view(template_name="settings_users.html"),
         name="settings_users"),

    # HOD Reports
    path('reports/attainment/',
         TemplateView.as_view(template_name="attainment_report.html"),
         name="attainment_report"),

    # Evidence
    path('evidence/',
         TemplateView.as_view(template_name="evidence_upload.html"),
         name="evidence_upload"),

    # -------------------------
    # Teacher pages
    # -------------------------
    path('teacher/create-assessment/',
         TemplateView.as_view(template_name="create_assessment.html"),
         name="create_assessment"),

    path('teacher/assessments/',
         TemplateView.as_view(template_name="assessment_list.html"),
         name="assessment_list"),

    path('teacher/upload-marks/',
         TemplateView.as_view(template_name="upload_marks.html"),
         name="upload_marks"),

    path('teacher/co-mapping/',
         TemplateView.as_view(template_name="co_mapping.html"),
         name="co_mapping"),

    path('teacher/po-mapping/',
         TemplateView.as_view(template_name="po_mapping.html"),
         name="po_mapping"),

    path('teacher/thresholds/',
         TemplateView.as_view(template_name="thresholds.html"),
         name="thresholds"),

    path('import-samples/',
         TemplateView.as_view(template_name="import_sample.html"),
         name="import_sample"),

    # -------------------------
    # Sample Pages
    # -------------------------
    path('samples/',
         TemplateView.as_view(template_name="import_sample.html"),
         name="samples"),
]