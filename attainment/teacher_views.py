"""
Teacher module views.

All views enforce:
  - @login_required
  - Course ownership (teacher_owns_course)
  - Semester lock on write operations (semester_unlocked)
  - Audit logging for critical actions
"""
import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Count
from django.utils import timezone

from attainment.models import (
    AcademicYear,
    Semester,
    Course,
    TeacherCourseAssignment,
    CourseOutcome,
    Assessment,
    AssessmentComponent,
    AssessmentType,
    StudentMark,
    MarksUpload,
    COAttainment,
    COSurveyAggregate,
    CQIAction,
    CqiStatus,
    GlobalConfig,
    AttainmentLevel,
)
from attainment.utils.decorators import teacher_owns_course, semester_unlocked
from attainment.utils.audit import log_action
from attainment.utils.attainment_engine import compute_attainment_for_course
from attainment.utils.rbac import role_required


# ------------------------------------------------------------------ helpers
BLOOM_CHOICES = [
    "Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create",
]


def _get_config():
    cfg = GlobalConfig.objects.first()
    if cfg is None:
        cfg = GlobalConfig.objects.create()
    return cfg


def _course_progress(course):
    """Return a dict of boolean progress flags for the course overview."""
    cos = CourseOutcome.objects.filter(course=course)
    co_count = cos.count()
    ia1 = Assessment.objects.filter(course=course, assessment_type=AssessmentType.IA1).first()
    ia2 = Assessment.objects.filter(course=course, assessment_type=AssessmentType.IA2).first()
    endsem = Assessment.objects.filter(course=course, assessment_type=AssessmentType.ENDSEM).first()

    questions_mapped = AssessmentComponent.objects.filter(
        assessment__course=course
    ).exists()

    marks_uploaded = StudentMark.objects.filter(
        question__assessment__course=course
    ).exclude(roll_no="").exists()

    attainment_calc = COAttainment.objects.filter(
        course_outcome__course=course
    ).exists()

    # CQI needed only if there's a CO below target
    cfg = _get_config()
    below_target = COAttainment.objects.filter(
        course_outcome__course=course,
        final_score__lt=cfg.po_target_level,
    ).exists() if attainment_calc else False

    cqi_submitted = CQIAction.objects.filter(
        course_outcome__course=course
    ).exists() if below_target else None  # None = not applicable

    return {
        "cos_defined": co_count > 0,
        "co_count": co_count,
        "ia1_created": ia1 is not None,
        "ia2_created": ia2 is not None,
        "endsem_created": endsem is not None,
        "questions_mapped": questions_mapped,
        "marks_uploaded": marks_uploaded,
        "attainment_calculated": attainment_calc,
        "cqi_needed": below_target,
        "cqi_submitted": cqi_submitted,
    }


# ==========================================================================
#  A. TEACHER DASHBOARD  (select academic year / semester, see courses)
# ==========================================================================

@login_required
@role_required('TEACHER')
def teacher_dashboard(request):
    """
    Teacher selects academic year + semester, sees only assigned courses.
    """
    academic_years = AcademicYear.objects.all().order_by("-name")
    selected_ay = request.GET.get("ay")
    selected_sem = request.GET.get("sem")

    semesters = []
    courses_data = []

    if selected_ay:
        semesters = Semester.objects.filter(
            academic_year_id=selected_ay
        ).order_by("number")

    if selected_ay and selected_sem:
        assigned = TeacherCourseAssignment.objects.filter(
            teacher=request.user,
            course__semester_id=selected_sem,
        ).select_related("course", "course__semester", "course__department")

        for a in assigned:
            courses_data.append({
                "assignment": a,
                "course": a.course,
                "progress": _course_progress(a.course),
            })

    context = {
        "academic_years": academic_years,
        "semesters": semesters,
        "selected_ay": int(selected_ay) if selected_ay else None,
        "selected_sem": int(selected_sem) if selected_sem else None,
        "courses_data": courses_data,
        "user_name": request.user.get_full_name() or request.user.username,
    }
    return render(request, "teacher/dashboard.html", context)


# ==========================================================================
#  A-bis. COURSE OVERVIEW
# ==========================================================================

@login_required
@role_required('TEACHER')
@teacher_owns_course
def course_overview(request, course_id, course=None):
    progress = _course_progress(course)
    semester = course.semester
    context = {
        "course": course,
        "semester": semester,
        "locked": semester.is_locked if semester else False,
        "progress": progress,
    }
    return render(request, "teacher/course_overview.html", context)


# ==========================================================================
#  B. COURSE OUTCOMES  (CRUD)
# ==========================================================================

@login_required
@role_required('TEACHER')
@teacher_owns_course
def manage_cos(request, course_id, course=None):
    """
    List + create COs.  Inline edit/delete via separate endpoints.
    """
    locked = course.semester.is_locked if course.semester else False
    cos = CourseOutcome.objects.filter(course=course).order_by("code")
    context = {
        "course": course,
        "cos": cos,
        "locked": locked,
        "bloom_choices": BLOOM_CHOICES,
    }
    return render(request, "teacher/course_outcomes.html", context)


@login_required
@role_required('TEACHER')
@teacher_owns_course
@semester_unlocked
def create_co(request, course_id, course=None):
    if request.method != "POST":
        return redirect("manage_cos", course_id=course_id)

    description = request.POST.get("description", "").strip()
    bloom = request.POST.get("bloom_level", "")

    if not description:
        messages.error(request, "Description is required.")
        return redirect("manage_cos", course_id=course_id)

    # Auto-generate code
    existing = CourseOutcome.objects.filter(course=course).count()
    code = f"CO{existing + 1}"
    # Ensure uniqueness
    while CourseOutcome.objects.filter(course=course, code=code).exists():
        existing += 1
        code = f"CO{existing + 1}"

    co = CourseOutcome.objects.create(
        course=course,
        code=code,
        description=description,
        bloom_levels=[bloom] if bloom else [],
    )
    log_action(request.user, "CREATE", "CourseOutcome", co.pk,
               f"Created {code} for {course.code}")
    messages.success(request, f"{code} created.")
    return redirect("manage_cos", course_id=course_id)


@login_required
@role_required('TEACHER')
@teacher_owns_course
@semester_unlocked
def edit_co(request, course_id, co_id, course=None):
    co = get_object_or_404(CourseOutcome, pk=co_id, course=course)
    if request.method != "POST":
        return redirect("manage_cos", course_id=course_id)

    description = request.POST.get("description", "").strip()
    bloom = request.POST.get("bloom_level", "")
    if description:
        co.description = description
    co.bloom_levels = [bloom] if bloom else co.bloom_levels
    co.save()
    log_action(request.user, "UPDATE", "CourseOutcome", co.pk,
               f"Edited {co.code}")
    messages.success(request, f"{co.code} updated.")
    return redirect("manage_cos", course_id=course_id)


@login_required
@role_required('TEACHER')
@teacher_owns_course
@semester_unlocked
def delete_co(request, course_id, co_id, course=None):
    co = get_object_or_404(CourseOutcome, pk=co_id, course=course)

    # Cannot delete if questions or marks reference it
    if AssessmentComponent.objects.filter(course_outcome=co).exists():
        messages.error(request,
                       f"Cannot delete {co.code}: questions are mapped to it.")
        return redirect("manage_cos", course_id=course_id)
    if StudentMark.objects.filter(question__course_outcome=co).exists():
        messages.error(request,
                       f"Cannot delete {co.code}: marks records exist.")
        return redirect("manage_cos", course_id=course_id)

    code = co.code
    co.delete()
    log_action(request.user, "DELETE", "CourseOutcome", co_id,
               f"Deleted {code} from {course.code}")
    messages.success(request, f"{code} deleted.")
    return redirect("manage_cos", course_id=course_id)


# ==========================================================================
#  C. ASSESSMENTS  (Create / list)
# ==========================================================================

@login_required
@role_required('TEACHER')
@teacher_owns_course
def manage_assessments(request, course_id, course=None):
    locked = course.semester.is_locked if course.semester else False
    assessments = Assessment.objects.filter(course=course).order_by("assessment_type")
    existing_types = set(assessments.values_list("assessment_type", flat=True))

    available_types = [
        (t.value, t.label)
        for t in [AssessmentType.IA1, AssessmentType.IA2, AssessmentType.ENDSEM]
        if t.value not in existing_types
    ]

    context = {
        "course": course,
        "assessments": assessments,
        "available_types": available_types,
        "locked": locked,
    }
    return render(request, "teacher/assessments.html", context)


@login_required
@role_required('TEACHER')
@teacher_owns_course
@semester_unlocked
def create_assessment(request, course_id, course=None):
    if request.method != "POST":
        return redirect("manage_assessments", course_id=course_id)

    a_type = request.POST.get("assessment_type", "")
    total_marks = request.POST.get("total_marks", "")
    date_str = request.POST.get("date", "")

    # Validate type
    valid_types = [AssessmentType.IA1, AssessmentType.IA2, AssessmentType.ENDSEM]
    if a_type not in [t.value for t in valid_types]:
        messages.error(request, "Invalid assessment type.")
        return redirect("manage_assessments", course_id=course_id)

    # One per type per course
    if Assessment.objects.filter(course=course, assessment_type=a_type).exists():
        messages.error(request, f"{a_type} already exists for this course.")
        return redirect("manage_assessments", course_id=course_id)

    try:
        tm = int(total_marks)
        if tm <= 0:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, "Total marks must be a positive integer.")
        return redirect("manage_assessments", course_id=course_id)

    name = dict(AssessmentType.choices).get(a_type, a_type)
    a = Assessment.objects.create(
        course=course,
        assessment_type=a_type,
        name=name,
        max_marks=tm,
        total_marks=tm,
        date=date_str or None,
    )
    log_action(request.user, "CREATE", "Assessment", a.pk,
               f"Created {name} for {course.code}")
    messages.success(request, f"{name} created.")
    return redirect("manage_assessments", course_id=course_id)


@login_required
@role_required('TEACHER')
@teacher_owns_course
@semester_unlocked
def delete_assessment(request, course_id, assessment_id, course=None):
    a = get_object_or_404(Assessment, pk=assessment_id, course=course)
    name = a.name
    a.delete()
    log_action(request.user, "DELETE", "Assessment", assessment_id,
               f"Deleted {name} from {course.code}")
    messages.success(request, f"{name} deleted.")
    return redirect("manage_assessments", course_id=course_id)


# ==========================================================================
#  D. QUESTION-TO-CO MAPPING
# ==========================================================================

@login_required
@role_required('TEACHER')
@teacher_owns_course
def manage_questions(request, course_id, assessment_id, course=None):
    locked = course.semester.is_locked if course.semester else False
    assessment = get_object_or_404(Assessment, pk=assessment_id, course=course)
    questions = AssessmentComponent.objects.filter(
        assessment=assessment
    ).select_related("course_outcome").order_by("component_number")
    cos = CourseOutcome.objects.filter(course=course).order_by("code")

    total_qmarks = questions.aggregate(s=Sum("max_marks"))["s"] or 0

    context = {
        "course": course,
        "assessment": assessment,
        "questions": questions,
        "cos": cos,
        "locked": locked,
        "total_qmarks": total_qmarks,
        "marks_mismatch": total_qmarks != (assessment.total_marks or assessment.max_marks),
    }
    return render(request, "teacher/question_mapping.html", context)


@login_required
@role_required('TEACHER')
@teacher_owns_course
@semester_unlocked
def save_questions(request, course_id, assessment_id, course=None):
    """
    Bulk save: reads rows from POST (question_code[], max_marks[], co_id[]).
    Replaces existing questions for this assessment.
    """
    if request.method != "POST":
        return redirect("manage_questions", course_id=course_id,
                        assessment_id=assessment_id)

    assessment = get_object_or_404(Assessment, pk=assessment_id, course=course)
    codes = request.POST.getlist("question_code")
    max_marks_list = request.POST.getlist("max_marks")
    co_ids = request.POST.getlist("co_id")

    if not codes:
        messages.error(request, "No questions provided.")
        return redirect("manage_questions", course_id=course_id,
                        assessment_id=assessment_id)

    errors = []
    rows = []
    for i, (code, mm, coid) in enumerate(zip(codes, max_marks_list, co_ids)):
        code = code.strip()
        if not code:
            errors.append(f"Row {i+1}: question code is empty.")
            continue
        try:
            mm_val = float(mm)
            if mm_val <= 0:
                raise ValueError
        except (ValueError, TypeError):
            errors.append(f"Row {i+1}: max marks must be a positive number.")
            continue
        if not coid:
            errors.append(f"Row {i+1}: CO must be selected.")
            continue
        co = CourseOutcome.objects.filter(pk=coid, course=course).first()
        if not co:
            errors.append(f"Row {i+1}: invalid CO selection.")
            continue
        rows.append((code, mm_val, co))

    if errors:
        messages.error(request, " | ".join(errors))
        return redirect("manage_questions", course_id=course_id,
                        assessment_id=assessment_id)

    # Check sum vs total_marks
    total = sum(r[1] for r in rows)
    expected = assessment.total_marks or assessment.max_marks
    if total != expected:
        messages.warning(
            request,
            f"Sum of question marks ({total}) ≠ assessment total ({expected}). "
            "Saved anyway — please verify."
        )

    with transaction.atomic():
        # Remove old questions (cascades to StudentMark.question FK)
        AssessmentComponent.objects.filter(assessment=assessment).delete()
        for code, mm_val, co in rows:
            AssessmentComponent.objects.create(
                assessment=assessment,
                component_number=code,
                max_marks=mm_val,
                course_outcome=co,
            )

    log_action(request.user, "SAVE", "QuestionMapping", assessment.pk,
               f"Saved {len(rows)} questions for {assessment.name}")
    messages.success(request, f"{len(rows)} questions saved.")
    return redirect("manage_questions", course_id=course_id,
                    assessment_id=assessment_id)


# ==========================================================================
#  E. MARKS UPLOAD  (CSV / Excel)
# ==========================================================================

@login_required
@role_required('TEACHER')
@teacher_owns_course
def marks_upload_page(request, course_id, assessment_id, course=None):
    locked = course.semester.is_locked if course.semester else False
    assessment = get_object_or_404(Assessment, pk=assessment_id, course=course)
    questions = AssessmentComponent.objects.filter(
        assessment=assessment
    ).order_by("component_number")

    uploads = MarksUpload.objects.filter(assessment=assessment).order_by("-uploaded_at")[:5]

    context = {
        "course": course,
        "assessment": assessment,
        "questions": questions,
        "uploads": uploads,
        "locked": locked,
    }
    return render(request, "teacher/marks_upload.html", context)


@login_required
@role_required('TEACHER')
@teacher_owns_course
@semester_unlocked
def marks_upload_process(request, course_id, assessment_id, course=None):
    """
    Parse CSV, validate, show preview.
    If POST has 'confirm', actually save.
    """
    if request.method != "POST":
        return redirect("marks_upload_page", course_id=course_id,
                        assessment_id=assessment_id)

    assessment = get_object_or_404(Assessment, pk=assessment_id, course=course)
    questions = AssessmentComponent.objects.filter(
        assessment=assessment
    ).order_by("component_number")

    if not questions.exists():
        messages.error(request, "Define and map questions before uploading marks.")
        return redirect("marks_upload_page", course_id=course_id,
                        assessment_id=assessment_id)

    q_map = {q.component_number: q for q in questions}
    expected_headers = sorted(q_map.keys())

    # ---- CONFIRM STEP ----
    if request.POST.get("confirm") == "1":
        return _confirm_marks(request, course, assessment, q_map)

    # ---- PARSE STEP ----
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        messages.error(request, "No file selected.")
        return redirect("marks_upload_page", course_id=course_id,
                        assessment_id=assessment_id)

    # Read CSV
    try:
        raw = uploaded_file.read()
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                text = raw.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        else:
            messages.error(request, "Unable to decode file encoding.")
            return redirect("marks_upload_page", course_id=course_id,
                            assessment_id=assessment_id)

        reader = csv.DictReader(io.StringIO(text))
        file_headers = [h.strip() for h in (reader.fieldnames or [])]
    except Exception as e:
        messages.error(request, f"File read error: {e}")
        return redirect("marks_upload_page", course_id=course_id,
                        assessment_id=assessment_id)

    # Validate headers
    if "RollNo" not in file_headers:
        messages.error(request, "First column must be 'RollNo'.")
        return redirect("marks_upload_page", course_id=course_id,
                        assessment_id=assessment_id)

    question_cols = [h for h in file_headers if h != "RollNo"]
    missing = set(expected_headers) - set(question_cols)
    extra = set(question_cols) - set(q_map.keys())
    if missing:
        messages.error(request,
                       f"Missing question columns: {', '.join(sorted(missing))}")
        return redirect("marks_upload_page", course_id=course_id,
                        assessment_id=assessment_id)
    if extra:
        messages.warning(request,
                         f"Extra columns ignored: {', '.join(sorted(extra))}")

    # Parse rows
    parsed_rows = []
    errors = []
    for i, row in enumerate(reader, start=2):
        roll = (row.get("RollNo") or "").strip()
        if not roll:
            errors.append(f"Row {i}: missing RollNo.")
            continue
        marks_dict = {}
        row_ok = True
        for qcode, q in q_map.items():
            raw_val = (row.get(qcode) or "").strip()
            if raw_val == "":
                marks_dict[qcode] = 0.0
            else:
                try:
                    val = float(raw_val)
                except ValueError:
                    errors.append(f"Row {i} ({roll}): '{qcode}' is not a number.")
                    row_ok = False
                    continue
                if val > q.max_marks:
                    errors.append(
                        f"Row {i} ({roll}): '{qcode}' marks {val} exceed max {q.max_marks}."
                    )
                    row_ok = False
                    continue
                if val < 0:
                    errors.append(f"Row {i} ({roll}): negative marks for '{qcode}'.")
                    row_ok = False
                    continue
                marks_dict[qcode] = val
        if row_ok:
            parsed_rows.append({"roll": roll, "marks": marks_dict})

    request.session["marks_preview"] = {
        "rows": parsed_rows,
        "errors": errors,
        "file_name": uploaded_file.name,
        "assessment_id": assessment.pk,
    }

    context = {
        "course": course,
        "assessment": assessment,
        "questions": questions,
        "parsed_rows": parsed_rows[:20],
        "total_rows": len(parsed_rows),
        "errors": errors,
        "file_name": uploaded_file.name,
    }
    return render(request, "teacher/marks_preview.html", context)


def _confirm_marks(request, course, assessment, q_map):
    """
    Final save: replace old marks for this assessment, insert new ones.
    """
    preview = request.session.pop("marks_preview", None)
    if not preview or preview.get("assessment_id") != assessment.pk:
        messages.error(request, "Preview expired. Please re-upload the file.")
        return redirect("marks_upload_page", course_id=course.pk,
                        assessment_id=assessment.pk)

    rows = preview["rows"]
    file_name = preview["file_name"]
    q_ids = [q.pk for q in q_map.values()]

    with transaction.atomic():
        # Delete old marks for this assessment's questions
        StudentMark.objects.filter(question_id__in=q_ids).delete()

        upload = MarksUpload.objects.create(
            assessment=assessment,
            file_name=file_name,
            uploaded_by=request.user.username,
            record_count=len(rows),
        )

        bulk = []
        for row_data in rows:
            roll = row_data["roll"]
            for qcode, val in row_data["marks"].items():
                q = q_map.get(qcode)
                if q:
                    bulk.append(StudentMark(
                        roll_no=roll,
                        marks=val,
                        question=q,
                        marks_upload=upload,
                    ))
        if bulk:
            StudentMark.objects.bulk_create(bulk)

    # Trigger attainment recalculation
    compute_attainment_for_course(course)

    log_action(request.user, "UPLOAD_MARKS", "Assessment", assessment.pk,
               f"Uploaded {len(rows)} students for {assessment.name}")
    messages.success(request,
                     f"Marks saved: {len(rows)} students, {len(bulk)} records. "
                     "Attainment recalculated.")
    return redirect("marks_upload_page", course_id=course.pk,
                    assessment_id=assessment.pk)


# ==========================================================================
#  F. CO ATTAINMENT RESULTS  (read-only)
# ==========================================================================

@login_required
@role_required('TEACHER')
@teacher_owns_course
def co_attainment_results(request, course_id, course=None):
    cfg = _get_config()
    cos = CourseOutcome.objects.filter(course=course).order_by("code")

    results = []
    for co in cos:
        att = COAttainment.objects.filter(course_outcome=co).first()
        survey = COSurveyAggregate.objects.filter(course_outcome=co).first()

        ia1_pct = att.ia1_level if att else None
        ia2_pct = att.ia2_level if att else None
        end_pct = att.end_sem_level if att else None

        def _pct_lvl(pct):
            if pct is None:
                return "—", "—"
            from attainment.utils.attainment_engine import _percent_to_level
            lvl = _percent_to_level(pct, cfg)
            return f"{pct:.1f}%", lvl.replace("LEVEL_", "L")

        ia1_str, ia1_lvl = _pct_lvl(ia1_pct)
        ia2_str, ia2_lvl = _pct_lvl(ia2_pct)
        end_str, end_lvl = _pct_lvl(end_pct)

        direct = att.direct_score if att else None
        indirect = att.indirect_score if att else None
        final = att.final_score if att else None
        level = att.level if att else None
        target = cfg.po_target_level

        achieved = final >= target if final is not None else False

        results.append({
            "co": co,
            "ia1_pct": ia1_str,
            "ia1_lvl": ia1_lvl,
            "ia2_pct": ia2_str,
            "ia2_lvl": ia2_lvl,
            "end_pct": end_str,
            "end_lvl": end_lvl,
            "direct": f"{direct:.2f}" if direct is not None else "—",
            "indirect": f"{indirect:.2f}" if indirect is not None else "N/A",
            "final": f"{final:.2f}" if final is not None else "—",
            "level": (level or "—").replace("LEVEL_", "L"),
            "target": f"{target:.1f}",
            "achieved": achieved,
        })

    context = {
        "course": course,
        "results": results,
        "config": cfg,
    }
    return render(request, "teacher/attainment_results.html", context)


@login_required
@role_required('TEACHER')
@teacher_owns_course
def recalculate_attainment(request, course_id, course=None):
    compute_attainment_for_course(course)
    log_action(request.user, "RECALCULATE", "COAttainment", course.pk,
               f"Manual recalculation for {course.code}")
    messages.success(request, "Attainment recalculated.")
    return redirect("co_attainment_results", course_id=course_id)


# ==========================================================================
#  G. CQI / ACTION TAKEN
# ==========================================================================

@login_required
@role_required('TEACHER')
@teacher_owns_course
def cqi_list(request, course_id, course=None):
    cfg = _get_config()
    cos = CourseOutcome.objects.filter(course=course).order_by("code")

    items = []
    for co in cos:
        att = COAttainment.objects.filter(course_outcome=co).first()
        final = att.final_score if att else None
        target = cfg.po_target_level
        below = final is not None and final < target

        cqi = CQIAction.objects.filter(
            course_outcome=co, created_by=request.user.username
        ).first()

        items.append({
            "co": co,
            "final_score": f"{final:.2f}" if final is not None else "—",
            "target": f"{target:.1f}",
            "below_target": below,
            "cqi": cqi,
        })

    context = {
        "course": course,
        "items": items,
    }
    return render(request, "teacher/cqi_list.html", context)


@login_required
@role_required('TEACHER')
@teacher_owns_course
def save_cqi(request, course_id, co_id, course=None):
    if request.method != "POST":
        return redirect("cqi_list", course_id=course_id)

    co = get_object_or_404(CourseOutcome, pk=co_id, course=course)
    action_taken = request.POST.get("action_taken", "").strip()
    remarks = request.POST.get("remarks", "").strip()
    status = request.POST.get("status", CqiStatus.PENDING)

    if not action_taken:
        messages.error(request, "Action taken is required.")
        return redirect("cqi_list", course_id=course_id)

    cqi, created = CQIAction.objects.update_or_create(
        course_outcome=co,
        created_by=request.user.username,
        defaults={
            "action_taken": action_taken,
            "remarks": remarks,
            "status": status,
        },
    )
    verb = "created" if created else "updated"
    log_action(request.user, "SAVE_CQI", "CQIAction", cqi.pk,
               f"CQI {verb} for {co.code} in {course.code}")
    messages.success(request, f"CQI for {co.code} {verb}.")
    return redirect("cqi_list", course_id=course_id)
