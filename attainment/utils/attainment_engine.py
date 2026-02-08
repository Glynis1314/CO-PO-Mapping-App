"""
Attainment calculation engine.

Computes:
  - Per-CO attainment percentage for each assessment type (IA1, IA2, ENDSEM)
  - Per-CO attainment level (LEVEL_0 … LEVEL_3) per assessment
  - Direct weighted CO score
  - Indirect CO score (from COSurveyAggregate)
  - Final CO score using GlobalConfig weightages

Method B:
  "Percentage of students scoring ≥ target-marks-percent of max marks
   for the questions mapped to the CO in a given assessment."
  That percentage is then mapped to a level using threshold bands.
"""
from django.utils import timezone
from attainment.models import (
    Assessment,
    AssessmentComponent,
    StudentMark,
    CourseOutcome,
    COAttainment,
    COSurveyAggregate,
    GlobalConfig,
    AttainmentLevel,
    AssessmentType,
)


def _get_config():
    """Return the single GlobalConfig row (create defaults if none)."""
    cfg = GlobalConfig.objects.first()
    if cfg is None:
        cfg = GlobalConfig.objects.create()
    return cfg


def _percent_to_level(pct, cfg):
    """Map a percentage to an AttainmentLevel string."""
    if pct >= cfg.level3_threshold:
        return AttainmentLevel.LEVEL_3
    elif pct >= cfg.level2_threshold:
        return AttainmentLevel.LEVEL_2
    elif pct >= cfg.level1_threshold:
        return AttainmentLevel.LEVEL_1
    return AttainmentLevel.LEVEL_0


def _level_to_numeric(lvl_str):
    """LEVEL_0 → 0, LEVEL_1 → 1, …"""
    mapping = {
        AttainmentLevel.LEVEL_0: 0.0,
        AttainmentLevel.LEVEL_1: 1.0,
        AttainmentLevel.LEVEL_2: 2.0,
        AttainmentLevel.LEVEL_3: 3.0,
    }
    return mapping.get(lvl_str, 0.0)


def compute_co_attainment_for_assessment(assessment, co, cfg):
    """
    For a given assessment and CO, compute:
      - attainment percentage (% students ≥ target)
      - attainment level
    Returns (pct, level_str) or (None, None) if no data.
    """
    questions = AssessmentComponent.objects.filter(
        assessment=assessment, course_outcome=co
    )
    if not questions.exists():
        return None, None

    total_max = sum(q.max_marks for q in questions)
    if total_max == 0:
        return None, None

    target_marks = total_max * (cfg.co_target_marks_percent / 100.0)

    # Gather distinct roll numbers that have marks for these questions
    q_ids = list(questions.values_list("id", flat=True))
    marks_qs = StudentMark.objects.filter(question_id__in=q_ids).exclude(
        roll_no=""
    )
    # Group by roll_no
    roll_totals = {}
    for sm in marks_qs:
        roll_totals.setdefault(sm.roll_no, 0.0)
        roll_totals[sm.roll_no] += (sm.marks or 0.0)

    if not roll_totals:
        return None, None

    total_students = len(roll_totals)
    passed = sum(1 for total in roll_totals.values() if total >= target_marks)
    pct = (passed / total_students) * 100.0
    level = _percent_to_level(pct, cfg)
    return round(pct, 2), level


def compute_attainment_for_course(course):
    """
    Recompute full CO attainment for every CO of a course.
    Saves / updates COAttainment rows.
    Returns list of COAttainment objects.
    """
    cfg = _get_config()
    cos = CourseOutcome.objects.filter(course=course)
    results = []

    for co in cos:
        ia1_pct, ia1_lvl = None, None
        ia2_pct, ia2_lvl = None, None
        end_pct, end_lvl = None, None

        # IA1
        ia1 = Assessment.objects.filter(
            course=course, assessment_type=AssessmentType.IA1
        ).first()
        if ia1:
            ia1_pct, ia1_lvl = compute_co_attainment_for_assessment(ia1, co, cfg)

        # IA2
        ia2 = Assessment.objects.filter(
            course=course, assessment_type=AssessmentType.IA2
        ).first()
        if ia2:
            ia2_pct, ia2_lvl = compute_co_attainment_for_assessment(ia2, co, cfg)

        # ENDSEM
        endsem = Assessment.objects.filter(
            course=course, assessment_type=AssessmentType.ENDSEM
        ).first()
        if endsem:
            end_pct, end_lvl = compute_co_attainment_for_assessment(endsem, co, cfg)

        # ----- Direct weighted score -----
        ia1_num = _level_to_numeric(ia1_lvl) if ia1_lvl else 0.0
        ia2_num = _level_to_numeric(ia2_lvl) if ia2_lvl else 0.0
        end_num = _level_to_numeric(end_lvl) if end_lvl else 0.0

        # Determine how many assessments actually have data
        w_sum = 0.0
        w_total = 0.0
        if ia1_lvl is not None:
            w_sum += ia1_num * cfg.ia1_weightage
            w_total += cfg.ia1_weightage
        if ia2_lvl is not None:
            w_sum += ia2_num * cfg.ia2_weightage
            w_total += cfg.ia2_weightage
        if end_lvl is not None:
            w_sum += end_num * cfg.end_sem_weightage
            w_total += cfg.end_sem_weightage

        direct_score = round(w_sum / w_total, 2) if w_total > 0 else None

        # ----- Indirect score (from survey aggregate) -----
        indirect_score = None
        try:
            survey = co.survey  # COSurveyAggregate (OneToOne)
            if survey and survey.responses > 0:
                indirect_score = round(survey.average_score, 2)
        except COSurveyAggregate.DoesNotExist:
            pass

        # ----- Final score -----
        final_score = None
        if direct_score is not None:
            if indirect_score is not None:
                final_score = round(
                    direct_score * cfg.direct_weightage
                    + indirect_score * cfg.indirect_weightage,
                    2,
                )
            else:
                final_score = direct_score

        final_level = _percent_to_level(
            (final_score / 3.0) * 100.0 if final_score else 0, cfg
        ) if final_score is not None else AttainmentLevel.LEVEL_0

        # ----- Persist -----
        att, _ = COAttainment.objects.update_or_create(
            course_outcome=co,
            defaults={
                "ia1_level": ia1_pct,
                "ia2_level": ia2_pct,
                "end_sem_level": end_pct,
                "direct_score": direct_score,
                "indirect_score": indirect_score,
                "final_score": final_score,
                "level": final_level,
                "attainment_percentage": ia1_pct,  # legacy compat
                "attainment_level": _level_to_numeric(final_level),
                "calculated_at": timezone.now(),
            },
        )
        results.append(att)

    return results
