from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from .forms import MarksUploadForm
from .models import MarksUpload, SemesterLock, AuditLog
from .utils.marks_parser import MarksValidationError, parse_marks_upload
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

