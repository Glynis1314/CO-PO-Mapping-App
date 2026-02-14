from django.urls import path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from . import views
from . import teacher_views as tv
from . import auth_views
from . import admin_views as av
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
    # ADMIN MODULE – full CRUD
    # ===========================

    # Admin Dashboard
    path('admin-panel/', av.admin_dashboard, name="admin_dashboard"),

    # Academic Years
    path('admin-panel/academic-years/', av.admin_academic_years, name="admin_academic_years"),
    path('admin-panel/academic-years/create/', av.admin_create_academic_year, name="admin_create_academic_year"),
    path('admin-panel/academic-years/<int:ay_id>/activate/', av.admin_activate_academic_year, name="admin_activate_academic_year"),
    path('admin-panel/academic-years/<int:ay_id>/delete/', av.admin_delete_academic_year, name="admin_delete_academic_year"),

    # Departments
    path('admin-panel/departments/', av.admin_departments, name="admin_departments"),
    path('admin-panel/departments/create/', av.admin_create_department, name="admin_create_department"),
    path('admin-panel/departments/<int:dept_id>/edit/', av.admin_edit_department, name="admin_edit_department"),
    path('admin-panel/departments/<int:dept_id>/delete/', av.admin_delete_department, name="admin_delete_department"),

    # Programs
    path('admin-panel/programs/', av.admin_programs, name="admin_programs"),
    path('admin-panel/programs/create/', av.admin_create_program, name="admin_create_program"),
    path('admin-panel/programs/<int:prog_id>/edit/', av.admin_edit_program, name="admin_edit_program"),
    path('admin-panel/programs/<int:prog_id>/delete/', av.admin_delete_program, name="admin_delete_program"),

    # Semesters
    path('admin-panel/semesters/', av.admin_semesters, name="admin_semesters"),
    path('admin-panel/semesters/create/', av.admin_create_semester, name="admin_create_semester"),
    path('admin-panel/semesters/<int:sem_id>/toggle-lock/', av.admin_toggle_semester_lock, name="admin_toggle_semester_lock"),
    path('admin-panel/semesters/<int:sem_id>/delete/', av.admin_delete_semester, name="admin_delete_semester"),

    # Courses
    path('admin-panel/courses/', av.admin_courses, name="admin_courses"),
    path('admin-panel/courses/create/', av.admin_create_course, name="admin_create_course"),
    path('admin-panel/courses/<int:course_id>/edit/', av.admin_edit_course, name="admin_edit_course"),
    path('admin-panel/courses/<int:course_id>/delete/', av.admin_delete_course, name="admin_delete_course"),

    # Users (admin-managed)
    path('admin-panel/users/', av.admin_users, name="admin_users"),
    path('admin-panel/users/create/', av.admin_create_user, name="admin_create_user"),
    path('admin-panel/users/<int:user_id>/edit/', av.admin_edit_user, name="admin_edit_user"),
    path('admin-panel/users/<int:user_id>/toggle-active/', av.admin_toggle_user_active, name="admin_toggle_user_active"),

    # Teachers (admin-managed) — manage teacher accounts and assign courses
    path('admin-panel/teachers/', av.admin_teachers, name="admin_teachers"),
    path('admin-panel/assign-course/', av.admin_assign_course, name="admin_assign_course"),
    path('admin-panel/teachers/<int:teacher_id>/unassign-course/<int:course_id>/', av.admin_unassign_course_from_teacher, name="admin_unassign_course_from_teacher"),

    # Settings (thresholds, weightages, change history)
    path('admin-panel/settings/', av.admin_settings, name='admin_settings'),

    # Admin API (cascading dropdowns)
    path('admin-panel/api/semesters/<int:ay_id>/', av.api_semesters_for_ay, name="api_semesters_for_ay"),
    path('admin-panel/api/programs/<int:dept_id>/', av.api_programs_for_dept, name="api_programs_for_dept"),

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