from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Student, Event, POSAccount, SpecialEvent, SystemSettings, CustomUser, Attendance
import csv
from io import TextIOWrapper


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['student_id', 'first_name', 'last_name', 'birthday', 'course', 'year', 'section', 'email']
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
        }


class StudentRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Student
        fields = ['profile_picture']

    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['email', 'profile_picture']


class StudentPasswordForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("New passwords do not match")

        return cleaned_data


class EventForm(forms.ModelForm):
    courses = forms.MultipleChoiceField(
        choices=Student.COURSE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    years = forms.MultipleChoiceField(
        choices=Student.YEAR_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    sections = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Enter sections separated by commas (e.g., A, B, C)'}),
        required=True,
        help_text='Separate multiple sections with commas'
    )

    class Meta:
        model = Event
        fields = ['title', 'date', 'start_time', 'end_time', 'has_afternoon_session', 
                  'afternoon_start_time', 'afternoon_end_time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'afternoon_start_time': forms.TimeInput(attrs={'type': 'time'}),
            'afternoon_end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean_sections(self):
        sections_str = self.cleaned_data.get('sections', '')
        sections = [s.strip() for s in sections_str.split(',') if s.strip()]
        return sections

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.courses = self.cleaned_data['courses']
        instance.years = self.cleaned_data['years']
        instance.sections = self.cleaned_data['sections']
        if commit:
            instance.save()
        return instance


class POSAccountForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = POSAccount
        fields = ['name', 'serial_number', 'display_mode']

    def save(self, commit=True):
        pos_account = super().save(commit=False)
        
        user = CustomUser.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            user_type='pos'
        )
        pos_account.user = user
        
        if commit:
            pos_account.save()
        return pos_account


class SpecialEventForm(forms.ModelForm):
    assigned_pos = forms.ModelMultipleChoiceField(
        queryset=POSAccount.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = SpecialEvent
        fields = ['title', 'start_date', 'end_date', 'start_time', 'end_time', 
                  'countdown_image', 'assigned_pos']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = ['system_name', 'logo']


class AdminPasswordChangeForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("New passwords do not match")

        return cleaned_data


class UnifiedLoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Username or Student ID'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )


class StudentIDVerificationForm(forms.Form):
    student_id = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your Student ID'})
    )


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        help_text='Upload a CSV file with columns: student_id, first_name, last_name, birthday, course, year, section, email'
    )

    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if not file.name.endswith('.csv'):
            raise forms.ValidationError('File must be a CSV file')
        return file


class AttendanceFilterForm(forms.Form):
    course = forms.ChoiceField(
        choices=[('', 'All Courses')] + list(Student.COURSE_CHOICES),
        required=False
    )
    year = forms.ChoiceField(
        choices=[('', 'All Years')] + list(Student.YEAR_CHOICES),
        required=False
    )
    section = forms.CharField(max_length=10, required=False)
    event = forms.ModelChoiceField(
        queryset=Event.objects.all(),
        required=False,
        empty_label='All Events'
    )
