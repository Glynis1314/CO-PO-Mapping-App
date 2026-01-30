from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from .forms import MarksUploadForm, SurveyUploadForm
from .models import MarksUpload, SemesterLock, AuditLog, SurveyUpload, COIndirectAttainment, POIndirectAttainment, CourseOutcome, ProgramOutcome
from .utils.marks_parser import MarksValidationError, parse_marks_upload
from .utils.survey_parser import SurveyValidationError, parse_survey_csv
from .tasks import import_marks_background


@login_required
def upload_marks(request):
    # Teacher-only access can be enforced here
    if request.method == 'POST':
        form = MarksUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            marks_upload = form.save(commit=False)
            marks_upload.uploaded_by = request.user
            marks_upload.status = 'PENDING'
            marks_upload.save()

            # Run validation
            try:
                result = parse_marks_upload(marks_upload.file, marks_upload.assessment)
                marks_upload.metadata = result.get('metadata')
                if result.get('validated'):
                    marks_upload.status = 'VALIDATED'
                else:
                    marks_upload.status = 'FAILED'
                    marks_upload.error_report = '\n'.join(result.get('errors', []))
                marks_upload.save()

                # Log upload
                AuditLog.objects.create(user=request.user, action='Marks file uploaded', object_type='MarksUpload', object_id=str(marks_upload.id), details={'filename': marks_upload.file.name, 'status': marks_upload.status})

                if marks_upload.status == 'VALIDATED':
                    messages.success(request, 'File uploaded and validated. Preview below.')
                    return redirect(reverse('marks_upload_preview', args=[marks_upload.id]))
                else:
                    messages.error(request, 'Upload failed validation. See errors below.')
                    return redirect(reverse('marks_upload_preview', args=[marks_upload.id]))

            except MarksValidationError as e:
                marks_upload.status = 'FAILED'
                marks_upload.error_report = str(e)
                marks_upload.save()
                messages.error(request, f'Validation error: {e}')
                return redirect(reverse('marks_upload_preview', args=[marks_upload.id]))
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = MarksUploadForm(user=request.user)
    return render(request, 'upload_marks.html', {'form': form})


@login_required
def upload_survey(request):
    if request.method == 'POST':
        form = SurveyUploadForm(request.POST, request.FILES)
        if form.is_valid():
            su = form.save(commit=False)
            su.uploaded_by = request.user

            # get uploaded file directly from request to avoid closed file issues
            uploaded_file = request.FILES.get('file')

            # validate CSV
            try:
                result = parse_survey_csv(uploaded_file, su.template)
            except SurveyValidationError as e:
                AuditLog.objects.create(user=request.user, action='Survey upload failed', object_type='SurveyUpload', object_id='-1', details={'error': str(e)})
                messages.error(request, f'Validation error: {e}')
                return redirect('upload_survey')

            # Save file, summary and finalize
            su.file = uploaded_file
            su.is_locked = True
            su.summary = result['summary']
            su.total_responses = result['total_responses']
            su.save()

            # Create COIndirectAttainment or POIndirectAttainment depending on template
            if su.template.survey_type == 'COURSE':
                # For each question code (CO1...), find the CourseOutcome for the selected course
                for code, data in su.summary.items():
                    try:
                        co = CourseOutcome.objects.get(course=su.course, code=code)
                    except CourseOutcome.DoesNotExist:
                        AuditLog.objects.create(user=request.user, action='COIndirect compute failed', object_type='SurveyUpload', object_id=str(su.id), details={'missing_co': code})
                        continue
                    avg = data['average']
                    COIndirectAttainment.objects.update_or_create(course_outcome=co, survey_upload=su, defaults={'indirect_score': avg, 'total_responses': data['total_responses']})
                    AuditLog.objects.create(user=request.user, action='COIndirect computed', object_type='COIndirectAttainment', object_id=f'{co.id}:{su.id}', details={'average': avg})
            else:
                # program survey -> create POIndirectAttainment
                for code, data in su.summary.items():
                    try:
                        po = ProgramOutcome.objects.get(code=code)
                    except ProgramOutcome.DoesNotExist:
                        AuditLog.objects.create(user=request.user, action='POIndirect compute failed', object_type='SurveyUpload', object_id=str(su.id), details={'missing_po': code})
                        continue
                    avg = data['average']
                    POIndirectAttainment.objects.update_or_create(program_outcome=po, survey_upload=su, defaults={'indirect_score': avg, 'total_responses': data['total_responses']})
                    AuditLog.objects.create(user=request.user, action='POIndirect computed', object_type='POIndirectAttainment', object_id=f'{po.id}:{su.id}', details={'average': avg})

            AuditLog.objects.create(user=request.user, action='Survey uploaded', object_type='SurveyUpload', object_id=str(su.id), details={'template': su.template.name, 'responses': su.total_responses})
            messages.success(request, 'Survey uploaded and summarized successfully.')
            return redirect('survey_upload_preview', su.id)
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = SurveyUploadForm()
    return render(request, 'upload_survey.html', {'form': form})


@login_required
def survey_upload_preview(request, upload_id):
    su = get_object_or_404(SurveyUpload, id=upload_id)
    if request.user != su.uploaded_by and not request.user.is_superuser:
        messages.error(request, 'Unauthorized')
        return redirect('index')
    return render(request, 'survey_upload_preview.html', {'survey_upload': su})


@login_required
def marks_upload_preview(request, upload_id):
    mu = get_object_or_404(MarksUpload, id=upload_id)
    # Only uploader or admins can preview
    if request.user != mu.uploaded_by and not request.user.is_superuser:
        messages.error(request, 'Unauthorized')
        return redirect('index')

    # Parse again for preview (if metadata not present)
    result = None
    if mu.metadata:
        # Use the saved metadata for header, but re-parse sample rows
        try:
            result = parse_marks_upload(mu.file, mu.assessment)
        except Exception as e:
            result = {'errors': [str(e)], 'validated': False, 'sample_rows': [], 'headers': []}
    else:
        try:
            result = parse_marks_upload(mu.file, mu.assessment)
        except Exception as e:
            result = {'errors': [str(e)], 'validated': False, 'sample_rows': [], 'headers': []}

    return render(request, 'upload_marks_preview.html', {'marks_upload': mu, 'result': result})


@login_required
def marks_upload_errors_csv(request, upload_id):
    mu = get_object_or_404(MarksUpload, id=upload_id)
    if request.user != mu.uploaded_by and not request.user.is_superuser:
        messages.error(request, 'Unauthorized')
        return redirect('index')

    metadata = mu.metadata or {}
    invalid = metadata.get('invalid_rows') or []
    if not invalid:
        messages.error(request, 'No invalid rows available')
        return redirect('marks_upload_preview', upload_id=mu.id)

    import csv
    from django.http import HttpResponse
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="marks_upload_{mu.id}_errors.csv"'

    writer = csv.writer(response)
    # header row
    headers = metadata.get('header', [])
    writer.writerow(['row_number', 'roll'] + headers[1:] + ['errors'])
    for ir in invalid:
        row_vals = [ir.get('row_number'), ir.get('roll')]
        values = ir.get('values', {})
        for h in headers[1:]:
            row_vals.append(values.get(h, ''))
        row_vals.append('; '.join(ir.get('errors', [])))
        writer.writerow(row_vals)

    return response


@login_required
def marks_upload_confirm(request, upload_id):
    mu = get_object_or_404(MarksUpload, id=upload_id)
    if request.method != 'POST':
        messages.error(request, 'Invalid request')
        return redirect('marks_upload_preview', upload_id=mu.id)

    # Only uploader or admin can start import
    if request.user != mu.uploaded_by and not request.user.is_superuser:
        messages.error(request, 'Unauthorized')
        return redirect('index')

    if mu.status != 'VALIDATED':
        messages.error(request, 'Upload is not validated and cannot be imported.')
        return redirect('marks_upload_preview', upload_id=mu.id)

    # Check semester lock for assessment
    sem = mu.assessment.course.semester
    if sem:
        if SemesterLock.objects.filter(semester=sem).exists():
            messages.error(request, 'Semester is locked; cannot import marks.')
            return redirect('marks_upload_preview', upload_id=mu.id)

    # Start import: background in normal run, synchronous in tests to avoid DB locking issues
    import sys
    from django.conf import settings
    try:
        if 'test' in sys.argv:
            from .tasks import import_marks_to_db
            import_marks_to_db(mu.id, request.user.id)
        else:
            import_marks_background(mu.id, request.user.id)
            mu.status = 'IMPORTED'
            mu.save()
    except Exception as e:
        mu.status = 'FAILED'
        mu.error_report = str(e)
        mu.save()
        messages.error(request, f'Import failed: {e}')
        return redirect('marks_upload_preview', upload_id=mu.id)

    messages.success(request, 'Import started. Refresh preview to see results.')
    return redirect('marks_upload_preview', upload_id=mu.id)

