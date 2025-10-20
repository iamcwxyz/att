from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import qrcode
from io import BytesIO
from django.core.files import File
import uuid
import base64



class SystemSettings(models.Model):
    system_name = models.CharField(max_length=200, default="Attendance System")
    logo = models.ImageField(upload_to='system/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return self.system_name

    @classmethod
    def get_settings(cls):
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('admin', 'Admin'),
        ('student', 'Student'),
        ('pos', 'POS'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')
    
    def __str__(self):
        return f"{self.username} ({self.user_type})"

class Student(models.Model):
    COURSE_CHOICES = (
        ('BSIT', 'BS Information Technology'),
        ('BSCS', 'BS Computer Science'),
        ('BSIS', 'BS Information Systems'),
        ('BSEMC', 'BS Entertainment and Multimedia Computing'),
    )
    
    YEAR_CHOICES = (
        ('1', '1st Year'),
        ('2', '2nd Year'),
        ('3', '3rd Year'),
        ('4', '4th Year'),
    )
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    student_id = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=50, blank=True, null=True)  # ✅ Added this line
    last_name = models.CharField(max_length=100)
    birthday = models.DateField(null=True, blank=True)
    course = models.CharField(max_length=10, choices=COURSE_CHOICES)
    year = models.CharField(max_length=1, choices=YEAR_CHOICES)
    section = models.CharField(max_length=10)
    email = models.EmailField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    is_registered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student_id} - {self.get_full_name()}"

    def get_full_name(self):
        # ✅ Adjusted to include middle initial or full middle name if available
        if self.middle_name:
            return f"{self.last_name}, {self.first_name} {self.middle_name[0]}."  # Middle initial format
        return f"{self.last_name}, {self.first_name}"

#//

class Event(models.Model):
    title = models.CharField(max_length=200)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    has_afternoon_session = models.BooleanField(default=False)
    afternoon_start_time = models.TimeField(null=True, blank=True)
    afternoon_end_time = models.TimeField(null=True, blank=True)
    
    courses = models.JSONField(default=list)
    years = models.JSONField(default=list)
    sections = models.JSONField(default=list)
    
    qr_code = models.ImageField(upload_to='qrcodes/', null=True, blank=True)
    qr_data = models.CharField(max_length=200, unique=True, editable=False)
    
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.title} - {self.date}"

    def save(self, *args, **kwargs):
        if not self.qr_data:
            self.qr_data = str(uuid.uuid4())
        
        if not self.qr_code:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            filename = f'event_{self.qr_data[:8]}.png'
            self.qr_code.save(filename, File(buffer), save=False)
        
        super().save(*args, **kwargs)

    def is_available_now(self):
        now = timezone.localtime()
        event_datetime = timezone.make_aware(
            timezone.datetime.combine(self.date, self.start_time)
        )
        countdown_start = event_datetime - timezone.timedelta(minutes=5)
        return now >= countdown_start and now.date() == self.date

    def is_student_eligible(self, student):
        if student.course not in self.courses:
            return False
        if student.year not in self.years:
            return False
        if student.section not in self.sections:
            return False
        return True


class Attendance(models.Model):
    SESSION_CHOICES = (
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
    )
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    session = models.CharField(max_length=10, choices=SESSION_CHOICES, default='morning')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'student', 'session')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.student.student_id} - {self.event.title} ({self.session})"


class POSAccount(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    display_mode = models.CharField(
        max_length=20,
        choices=(('qr', 'QR Code Display'), ('manual', 'Manual Entry')),
        default='qr'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

#//
class SpecialEvent(models.Model):
    title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='event_images/', blank=True, null=True)
    countdown_image = models.ImageField(upload_to='countdown_images/', blank=True, null=True)
    qr_code = models.ImageField(upload_to='special_qrcodes/', blank=True, null=True)
    qr_data = models.CharField(max_length=255, unique=True, editable=False)
    assigned_pos = models.ManyToManyField('POSAccount', related_name='special_events', blank=True)

    def generate_qr(self):
        data = f"Event: {self.title}\nStart: {self.start_date}\nEnd: {self.end_date}"
        qr = qrcode.make(data)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('utf-8')}"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.qr_data:
            self.qr_data = f"special_{uuid.uuid4()}"
        
        if not self.qr_code:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            filename = f'special_{self.qr_data[:8]}.png'
            self.qr_code.save(filename, File(buffer), save=False)
        
        super().save(*args, **kwargs)

    def is_active_now(self):
        now = timezone.localtime()
        return (
            self.start_date <= now.date() <= self.end_date and
            self.start_time and self.end_time and
            self.start_time <= now.time() <= self.end_time
        )

#/// 

class SpecialEventAttendance(models.Model):
    special_event = models.ForeignKey(SpecialEvent, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='special_attendances')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('special_event', 'student')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.student.student_id} - {self.special_event.title}"
