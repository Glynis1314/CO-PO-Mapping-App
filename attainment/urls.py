from django.urls import path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from . import views
from . import teacher_views as tv
from . import auth_views
from .utils.rbac import role_required


def _protected_template(template, *roles):
    """Return a login_required + role_required TemplateView."""
    view = TemplateView.as_view(template_name=template)
    if roles:
        view = role_required(*roles)(view)
    view = login_required(view)
    return view


urlpatterns = [

    # -------------------------
    # Authentication
    # -------------------------
    path('login/', auth_views.login_view, name="login"),
    path('logout/', auth_views.logout_view, name="logout"),

    # -------------------------
    # Landing / Dashboards
    # -------------------------
    path('', views.index_view, name="index"),

    path('hod/dashboard/', views.dashboard_hod, name="dashboard_hod"),

    path('teacher/dashboard/',
         tv.teacher_dashboard,
         name="teacher_dashboard"),

    path('principal/dashboard/',
         views.principal_dashboard,
         name="dashboard_principal"),
     
    # -------------------------
    # HOD pages (protected)
    # -------------------------
    path('subjects/',
         _protected_template("subjects.html", 'HOD', 'ADMIN'),
         name="subjects"),

     # Path for assigning and saving the assigned subjects 
    path('assign-subjects/', views.assign_subjects_view, name='assign_subjects'),
    path('assign-subjects/save/', views.assign_subject_action, name='assign_subject'),

     # Path for adding the academic year and create the year 
    path('academic-years/', views.academic_years_list, name='academic_years_list'),
    path('academic-years/create/', views.create_academic_year, name='create_academic_year'),

    path('settings/users/',
         _protected_template("settings_users.html", 'HOD', 'ADMIN'),
         name="settings_users"),

    # HOD Reports
    path('reports/attainment/', views.attainment_report_view, name='attainment_report'),
    path('reports/gap-analysis/', views.gap_analysis_view, name='gap_analysis'),

    # Evidence
    path('evidence/',
         _protected_template("evidence_upload.html", 'HOD', 'ADMIN'),
         name="evidence_upload"),

    # ===========================
    # TEACHER MODULE – full CRUD
    # ===========================

    # A. Course overview
    path('teacher/course/<int:course_id>/',
         tv.course_overview, name="course_overview"),

    # B. Course Outcomes CRUD
    path('teacher/course/<int:course_id>/cos/',
         tv.manage_cos, name="manage_cos"),
    path('teacher/course/<int:course_id>/cos/create/',
         tv.create_co, name="create_co"),
    path('teacher/course/<int:course_id>/cos/<int:co_id>/edit/',
         tv.edit_co, name="edit_co"),
    path('teacher/course/<int:course_id>/cos/<int:co_id>/delete/',
         tv.delete_co, name="delete_co"),

    # C. Assessments CRUD
    path('teacher/course/<int:course_id>/assessments/',
         tv.manage_assessments, name="manage_assessments"),
    path('teacher/course/<int:course_id>/assessments/create/',
         tv.create_assessment, name="create_assessment"),
    path('teacher/course/<int:course_id>/assessments/<int:assessment_id>/delete/',
         tv.delete_assessment, name="delete_assessment"),

    # D. Question-to-CO mapping
    path('teacher/course/<int:course_id>/assessments/<int:assessment_id>/questions/',
         tv.manage_questions, name="manage_questions"),
    path('teacher/course/<int:course_id>/assessments/<int:assessment_id>/questions/save/',
         tv.save_questions, name="save_questions"),

    # E. Marks upload
    path('teacher/course/<int:course_id>/assessments/<int:assessment_id>/marks/',
         tv.marks_upload_page, name="marks_upload_page"),
    path('teacher/course/<int:course_id>/assessments/<int:assessment_id>/marks/upload/',
         tv.marks_upload_process, name="marks_upload_process"),

    # F. CO Attainment results (read-only)
    path('teacher/course/<int:course_id>/attainment/',
         tv.co_attainment_results, name="co_attainment_results"),
    path('teacher/course/<int:course_id>/attainment/recalculate/',
         tv.recalculate_attainment, name="recalculate_attainment"),

    # G. CQI / Action Taken
    path('teacher/course/<int:course_id>/cqi/',
         tv.cqi_list, name="cqi_list"),
    path('teacher/course/<int:course_id>/cqi/<int:co_id>/save/',
         tv.save_cqi, name="save_cqi"),

    # -------------------------
    # Legacy static teacher pages (kept for backward compat)
    # -------------------------
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

    path('samples/',
         TemplateView.as_view(template_name="import_sample.html"),
         name="samples"),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)