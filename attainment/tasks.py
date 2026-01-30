import threading
from django.db import transaction
from .models import MarksUpload, Student, StudentMark, AssessmentComponent, AuditLog


def import_marks_to_db(marks_upload_id, started_by_id):
    """Synchronous import function: performs DB operations to import marks."""
    mu = MarksUpload.objects.get(id=marks_upload_id)
    mu.status = 'IMPORTED'
    mu.save()

    # parse metadata saved earlier should contain header info
    metadata = mu.metadata or {}
    header = metadata.get('header', [])
    # Build component map
    components = AssessmentComponent.objects.filter(assessment=mu.assessment)
    component_map = {c.component_number: c for c in components}

    # Re-parse file to iterate all rows (to avoid missing rows outside preview)
    # Use the same parser as validation: import inside parser
    from .utils.marks_parser import parse_csv_file, parse_xlsx_file
    filename = mu.file.name.lower()
    f = mu.file
    if filename.endswith('.csv'):
        rows = parse_csv_file(f)
    else:
        rows = parse_xlsx_file(f)

    created_marks = 0
    with transaction.atomic():
        for row in rows[1:]:
            row = [str(c).strip() if c is not None else '' for c in row]
            if not row or len(row) == 0:
                continue
            roll = row[0]
            student, _ = Student.objects.get_or_create(roll_number=roll, defaults={'department': mu.assessment.course.department, 'name': ''})

            for col_idx, colname in enumerate(header[1:], start=1):
                if col_idx < len(row):
                    val = row[col_idx]
                    try:
                        val_num = float(val) if val != '' else 0.0
                    except Exception:
                        val_num = 0.0
                else:
                    val_num = 0.0
                comp = component_map.get(colname)
                if not comp:
                    continue
                StudentMark.objects.update_or_create(student=student, component=comp, defaults={'marks_obtained': val_num})
                created_marks += 1

    mu.metadata = {**(mu.metadata or {}), 'imported_marks': created_marks}
    mu.save()

    AuditLog.objects.create(user_id=started_by_id, action='Marks imported', object_type='MarksUpload', object_id=str(mu.id), details={'imported_marks': created_marks})


def import_marks_background(marks_upload_id, started_by_id):
    """Run the import asynchronously in a background thread."""
    def _run():
        try:
            import_marks_to_db(marks_upload_id, started_by_id)
        except Exception as exc:
            mu = MarksUpload.objects.get(id=marks_upload_id)
            mu.status = 'FAILED'
            mu.error_report = str(exc)
            mu.save()
            AuditLog.objects.create(user_id=started_by_id, action='Marks import failed', object_type='MarksUpload', object_id=str(mu.id), details={'error': str(exc)})

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t