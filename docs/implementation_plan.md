# Implementation Plan — CO–PO Attainment System

This file maps out the next development steps to fully realize the system per the prompt.

## Prioritized Workstreams

1. Core data and governance (done)
   - Models created/updated in `attainment.models`.
   - Admin registrations for quick data entry.
   - `seed_initial` management command to bootstrap default configuration.

2. CSV/Excel upload parsers & validators (high priority)
   - Marks upload parser:
     - Accept only exact file format: first column `RollNo`, columns matching `AssessmentComponent.component_number`.
     - Validate: all question IDs exist; marks ≤ component.max_marks; empty -> 0.
     - Require that all components are mapped to COs before upload.
     - Provide preview with per-row errors and reject on critical failures.
     - On successful import, create `Student` records as needed and `StudentMark` rows and set `MarksUpload.status` to `IMPORTED`.
   - Survey upload parser:
     - Accept CSV with columns matching `SurveyQuestion.code`.
     - Validate Likert responses (Strongly Agree/Agree/Neutral/Disagree) exactly.
     - Produce `SurveyUpload.summary` and set `is_locked=True`.

3. Attainment computation services
   - Implement reusable functions/services to compute:
     - Per-assessment CO attainment (per student checks against threshold)
     - Direct CO attainment (combine IA-1/IA-2/End weighted)
     - Indirect CO attainment from `SurveyUpload` (0–3 scale averages)
     - Final CO attainment (Direct × direct_weight + Indirect × indirect_weight)
     - Course-level PO computation (weighted CO × mapping / total mapping)
     - Program-level PO aggregation (average across contributing courses)
   - Each computation should produce `AuditLog` entries and store results in `COAttainment`, `COFinalAttainment`, `CoursePOAttainment`, `ProgramPOAttainment`.

4. Role-based UI and dashboards (Admin/HOD/Teacher)
   - Teacher pages: assigned courses, define COs (bloom level), create assessments and components, upload marks (with preview and validation), view CO attainment, raise CQI actions.
   - HOD pages: view department courses, CO/PO attainment, review CQI actions, assign teachers.
   - Admin pages: global configuration (locked), create programs/departments/semesters, run final locking for semester, view audit logs, export reports.

5. Reporting & export (NBA-ready)
   - Generate course-wise, program-wise, department-wise, and semester-wise reports.
   - Exports: Excel & PDF (with details: target, achieved values, levels, CQI actions).

6. Security, testing, and audits
   - Strict unit tests for parsers and computation logic.
   - Integration tests for end-to-end upload → computation → reporting.
   - Add audit trails for critical operations.

## Notes & Assumptions
- Global governance (targets, weightages) are centrally enforced via `GlobalConfig` and should only be editable by Admin.
- Teachers only enter academic inputs (CO descriptions, bloom levels, questions mapping, marks) — no thresholds or weights.
- Semester locking is required before reporting; locked data is immutable and auditable.

---

If you want, I can begin implementing the following next items in this order:
1. CSV validation and upload preview for marks (Teacher flow)
2. Survey CSV parsing and summarization (Admin/Teacher flow)
3. Computation services for CO and PO attainment
4. Basic dashboards and reporting pages with export

Tell me which item to start with and I will implement it in the repository.