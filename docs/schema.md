# CO–PO Attainment System — Database Schema

This document describes the database schema implemented in the `attainment` app and how it maps to the OBE/NBA requirements described in the prompt.

---

## High level entities

- AcademicYear: e.g., `2025-26` (name), active flag.
- Semester: `ODD` / `EVEN` per `AcademicYear`. Can be locked.
- Department: e.g., CSE, IT, Mechanical.
- Program: e.g., B.Tech CSE (belongs to a Department).
- Course: course code/name. Linked to `Department`, `Program`, `AcademicYear`, & `Semester`. `is_first_year_course` marks the First Year courses.
- UserProfile: extends `auth.User` with `role` (ADMIN/HOD/TEACHER) and optional `department`/`program`.

## Outcomes and mappings

- ProgramOutcome: PO1..PO12 (code, description)
- CourseOutcome: CO1..CON (per course) with `bloom_level` and `expected_proficiency` (per-student threshold, default 60%). Unique per (course + code).
- COtoPOMapping: articulates contribution of a CO to a PO using levels {1,2,3}.

## Assessments & components

- Assessment: assessment records with `assessment_category` (IA1, IA2, END) and `max_marks`. Each assessment belongs to a `Course`.
- AssessmentComponent: component/question (Q1, Q2...) inside an Assessment. Links to single `CourseOutcome`. Unique per (assessment, component_number).
- Student: student record (roll_number, name, department).
- StudentMark: mark obtained by a student per `AssessmentComponent`.

## Uploads and survey templates

- MarksUpload: stores uploaded file for an `Assessment` with status, validation metadata and error report. Audit-friendly (timestamps + uploader).
- SurveyTemplate and SurveyQuestion: Admin-defined survey templates for Course Exit / Program Exit. SurveyQuestion codes map to CO/PO codes (CO1, PO2, ...)
- SurveyUpload: stores uploaded CSV of survey responses (locked/read-only after upload) with a `summary` (counts), total_responses and timestamp.

## Attainment results

- COIndirectAttainment: indirect attainment computed from `SurveyUpload` per `CourseOutcome` (score 0–3, total_responses recorded).
- COAttainment: direct attainment records (existing model - percentage, level). Used to store computed results from marks.
- COFinalAttainment: final combined CO attainment (direct + indirect with global weights). Stores final value and attainment level.
- CoursePOAttainment: per-course PO attainment values (derived from CO×mapping formula).
- ProgramPOAttainment: aggregated program PO attainment values from contributing courses.

## CQI, locking and audit

- CQIAction: actions taken by teachers when COs fall below target. Tracks status and HOD review/remarks.
- SemesterLock: A lock record for a `Semester` when Admin/HOD freezes data for auditing.
- AuditLog: Generic auditable trail for critical actions (marks uploads, mapping changes, survey uploads, locks, etc.) with JSON details.
- GlobalConfig: Central system governance: CO target percent, student threshold percent, attainment level thresholds, assessment weightages (IA1=20, IA2=20, End=60), direct/indirect weights (0.8/0.2), PO target (2.5). `locked` marks whether config changes should be restricted to Admin.

## Important constraints & governance rules enforced by schema

- CO-to-PO mapping is stored and auditable (changes expected to be logged to `AuditLog`).
- `AssessmentComponent` mapping to `CourseOutcome` is mandatory.
- `MarksUpload` includes metadata that is used by the upload parser to enforce exact question codes and to reject uploads when mappings are not complete.
- `SurveyUpload` is read-only after uploading and carries an uneditable summary.
- `CourseOutcome` is unique per (course, code) and stores Bloom level and expected proficiency.

## Notes on calculations (business logic — to be implemented in services / model methods)

- Direct CO attainment: for every assessment (IA-1, IA-2, End), group components by CO, compute per-student CO marks and check if they reach `co_student_threshold_percent` (60% by default). Count % of students meeting threshold to get per-assessment CO attainment percentage. Convert percentage to attainment level using `GlobalConfig.attainment_thresholds`. Combine assessment levels using `ia1_weight`, `ia2_weight`, `end_sem_weight` into Direct CO score.

- Indirect CO attainment: use `SurveyUpload.summary` for the course exit survey; map Likert answers to 3/2/1/0 and compute average per CO → store in `COIndirectAttainment`.

- Final CO = (Direct × direct_weight) + (Indirect × indirect_weight). Store in `COFinalAttainment` and compare with PO target to raise CQI if needed.

- Course PO = Σ (CO_final_value × mapping_level) / Σ(mapping_level).
- Program PO = average of contributing course PO values.

## Next steps & TODOs

1. Implement upload parsers and CSV validators for `MarksUpload` and `SurveyUpload` that strictly enforce the formats described in the prompt.
2. Implement services to compute `COAttainment`, `COIndirectAttainment`, `COFinalAttainment`, `CoursePOAttainment`, and `ProgramPOAttainment` and write audit log entries.
3. Implement role-based access control and UI views (Admin dashboard, HOD dashboard, Teacher dashboard) and file upload flows with preview + validation report.
4. Add tests to validate calculations (edge cases: missing student marks, zero responses, more students than expected, invalid question ids).

---

This schema is deliberately normalized and audit-focused to match NBA-compliant evidence needs.
