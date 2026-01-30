from django import forms
from .models import Assessment, MarksUpload

class MarksUploadForm(forms.ModelForm):
    class Meta:
        model = MarksUpload
        fields = ['assessment', 'file']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Optionally, filter assessments to teacher's assigned courses
        if user is not None and hasattr(user, 'userprofile') and user.userprofile.role == 'TEACHER':
            self.fields['assessment'].queryset = Assessment.objects.filter(course__teachercourseassignment__teacher=user)
