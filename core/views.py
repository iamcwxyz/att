from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import Student, Event, Attendance, POSAccount, SpecialEvent, SpecialEventAttendance, SystemSettings, CustomUser
from .forms import *
import csv
from datetime import datetime, timedelta
from io import TextIOWrapper
from django.shortcuts import render, get_object_or_404, redirect
from .models import SpecialEvent
from .forms import SpecialEventForm
import qrcode
import io
import base64
from django.shortcuts import render
from .models import Event
import qrcode
import io
import base64
from datetime import datetime, time
from django.shortcuts import render
from .models import Event
from django.utils import timezone
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

def dashboard(request):
    now = timezone.now()
    special_events = Event.objects.all()

    # Generate QR code if missing
    for event in special_events:
        if not event.qr_code:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f"{event.title} - {event.start_datetime}")
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')

            buffer = BytesIO()
            img.save(buffer, format='PNG')
            file_name = f"event_{event.id}_qr.png"
            event.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=True)

        # Add a helper property for template
        event.is_active_now = event.start_datetime <= now <= event.end_datetime

    context = {
        "special_events": special_events
    }
    return render(request, "pos_dashboard.html", context)



def edit_special_event(request, event_id):
    event = get_object_or_404(SpecialEvent, id=event_id)
    
    if request.method == 'POST':
        form = SpecialEventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            # Redirect to the events table after successful update
            return redirect('manage_special_events')
    else:
        form = SpecialEventForm(instance=event)
    
    return render(request, 'edit_special_event.html', {'form': form, 'event': event})


def unified_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UnifiedLoginForm(request, data=request.POST)
        username_or_id = request.POST.get('username')
        password = request.POST.get('password')
        
        user = None
        try:
            student = Student.objects.get(student_id=username_or_id, is_registered=True)
            if student.user:
                user = authenticate(username=student.user.username, password=password)
        except Student.DoesNotExist:
            user = authenticate(username=username_or_id, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials')
    else:
        form = UnifiedLoginForm()
    
    return render(request, 'login.html', {'form': form})


def student_registration_check(request):
    if request.method == 'POST':
        form = StudentIDVerificationForm(request.POST)
        if form.is_valid():
            student_id = form.cleaned_data['student_id']
            try:
                student = Student.objects.get(student_id=student_id)
                if student.is_registered:
                    messages.error(request, 'This student ID is already registered. Please login.')
                    return redirect('login')
                else:
                    return redirect('student_registration', student_id=student_id)
            except Student.DoesNotExist:
                messages.error(request, 'Student ID not found. Please wait for the admin to add you to the system.')
                return redirect('registration_check')
    else:
        form = StudentIDVerificationForm()
    
    return render(request, 'registration_check.html', {'form': form})


def student_registration(request, student_id):
    student = get_object_or_404(Student, student_id=student_id, is_registered=False)
    
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST, request.FILES, student=student)
        if form.is_valid():
            password = form.cleaned_data['password']
            
            user = CustomUser.objects.create_user(
                username=student_id,
                password=password,
                user_type='student'
            )
            
            student.user = user
            student.profile_picture = form.cleaned_data.get('profile_picture')
            student.is_registered = True
            student.save()
            
            messages.success(request, 'Successfully Registered! You can now login.')
            return redirect('login')
    else:
        form = StudentRegistrationForm(student=student)
    
    return render(request, 'student_registration.html', {'form': form, 'student': student})


from datetime import datetime

@login_required
def dashboard(request):
    now = timezone.localtime()  # timezone-aware current time
    special_events = Event.objects.all()

    for event in special_events:
        # Combine date and time fields
        start_dt = datetime.combine(event.date, event.start_time)
        end_dt = datetime.combine(event.date, event.end_time)

        # Make timezone aware if your times are naive
        start_dt = timezone.make_aware(start_dt)
        end_dt = timezone.make_aware(end_dt)

        # Check if the event is active now
        event.is_active_now = start_dt <= now <= end_dt

        # Generate QR code dynamically
        if event.is_active_now:
            qr = qrcode.QRCode(version=1, box_size=5, border=4)
            qr.add_data(f"https://example.com/events/{event.id}")  # Customize URL
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            event.qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        else:
            event.qr_code_base64 = None

    context = {
        'special_events': special_events,
    }
    return render(request, 'pos_dashboard.html', context)

###
@login_required
def manage_students(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    search_query = request.GET.get('search', '')
    students = Student.objects.all()
    
    if search_query:
        students = students.filter(
            Q(student_id__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    paginator = Paginator(students, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'admin/manage_students.html', context)


@login_required
def add_student(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student added successfully')
            return redirect('manage_students')
    else:
        form = StudentForm()
    
    return render(request, 'admin/add_student.html', {'form': form})


@login_required
def edit_student(request, student_id):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully')
            return redirect('manage_students')
    else:
        form = StudentForm(instance=student)
    
    return render(request, 'admin/edit_student.html', {'form': form, 'student': student})


@login_required
def delete_student(request, student_id):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        if student.user:
            student.user.delete()
        student.delete()
        messages.success(request, 'Student deleted successfully')
    
    return redirect('manage_students')


@login_required
def view_student(request, student_id):
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    student = get_object_or_404(Student, id=student_id)
    data = {
        'student_id': student.student_id,
        'first_name': student.first_name,
        'last_name': student.last_name,
        'birthday': student.birthday.strftime('%Y-%m-%d'),
        'course': student.get_course_display(),
        'year': student.get_year_display(),
        'section': student.section,
        'email': student.email or 'N/A',
        'is_registered': student.is_registered,
        'profile_picture': student.profile_picture.url if student.profile_picture else None,
    }
    return JsonResponse(data)

#change here naaaaa

@login_required
def import_students_csv(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            decoded_file = TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.DictReader(decoded_file)
            
            created_count = 0
            updated_count = 0
            
            for row in reader:
                student_id = row.get('student_id', '').strip()
                if not student_id:
                    continue

                # Safely parse birthday
                birthday_str = row.get('birthday', '').strip()
                birthday = None
                if birthday_str and birthday_str.lower() not in ['n/a', 'none', '00/00/0000', '00-00-0000', '0']:
                    try:
                        # Try standard YYYY-MM-DD
                        birthday = datetime.strptime(birthday_str, '%Y-%m-%d').date()
                    except ValueError:
                        try:
                            # Try alternative format DD/MM/YYYY
                            birthday = datetime.strptime(birthday_str, '%d/%m/%Y').date()
                        except ValueError:
                            birthday = None

                try:
                    # Update existing student
                    student = Student.objects.get(student_id=student_id)
                    student.course = row.get('course', student.course).strip()
                    student.year = row.get('year', student.year).strip()
                    student.section = row.get('section', student.section).strip()
                    student.save()
                    updated_count += 1
                except Student.DoesNotExist:
                    # Create new student
                    Student.objects.create(
                        student_id=student_id,
                        first_name=row.get('first_name', '').strip(),
                        last_name=row.get('last_name', '').strip(),
                        birthday=birthday,
                        course=row.get('course', '').strip(),
                        year=row.get('year', '').strip(),
                        section=row.get('section', '').strip(),
                        email=row.get('email', '').strip() or None,
                    )
                    created_count += 1
            
            messages.success(request, f'Imported successfully: {created_count} created, {updated_count} updated')
            return redirect('manage_students')
    else:
        form = CSVUploadForm()
    
    return render(request, 'admin/import_students.html', {'form': form})

#end na here

@login_required
def export_attendance(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    course = request.GET.get('course', '')
    year = request.GET.get('year', '')
    section = request.GET.get('section', '')
    event_id = request.GET.get('event', '')
    
    attendances = Attendance.objects.select_related('student', 'event').all()
    
    if course:
        attendances = attendances.filter(student__course=course)
    if year:
        attendances = attendances.filter(student__year=year)
    if section:
        attendances = attendances.filter(student__section=section)
    if event_id:
        attendances = attendances.filter(event_id=event_id)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student ID', 'Name', 'Course', 'Year', 'Section', 'Event', 'Session', 'Timestamp'])
    
    for attendance in attendances:
        writer.writerow([
            attendance.student.student_id,
            attendance.student.get_full_name(),
            attendance.student.get_course_display(),
            attendance.student.get_year_display(),
            attendance.student.section,
            attendance.event.title,
            attendance.get_session_display(),
            attendance.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        ])
    
    return response


@login_required
def manage_events(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    events = Event.objects.all().order_by('-date', '-start_time')
    
    paginator = Paginator(events, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin/manage_events.html', {'page_obj': page_obj})


@login_required
def add_event(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            messages.success(request, 'Event created successfully')
            return redirect('manage_events')
    else:
        form = EventForm()
    
    return render(request, 'admin/add_event.html', {'form': form})


@login_required
def edit_event(request, event_id):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    event = get_object_or_404(Event, id=event_id)
    
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully')
            return redirect('manage_events')
    else:
        initial_data = {
            'courses': event.courses,
            'years': event.years,
            'sections': ', '.join(event.sections) if event.sections else '',
        }
        form = EventForm(instance=event, initial=initial_data)
    
    return render(request, 'admin/edit_event.html', {'form': form, 'event': event})


@login_required
def delete_event(request, event_id):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully')
    
    return redirect('manage_events')


@login_required
def view_event_qr(request, event_id):
    if request.user.user_type not in ['admin', 'pos']:
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    event = get_object_or_404(Event, id=event_id)
    now = timezone.localtime()
    
    context = {
        'event': event,
        'now': now,
    }
    return render(request, 'admin/view_event_qr.html', context)


@login_required
def scan_qr(request):
    if request.user.user_type != 'student':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    return render(request, 'student/scan_qr.html')


@login_required
def process_attendance(request):
    if request.method == 'POST' and request.user.user_type == 'student':
        qr_data = request.POST.get('qr_data')
        
        try:
            event = Event.objects.get(qr_data=qr_data)
            student = request.user.student
            
            if not event.is_student_eligible(student):
                return JsonResponse({'success': False, 'message': 'You are not eligible for this event'})
            
            now = timezone.localtime()
            if now.date() != event.date:
                return JsonResponse({'success': False, 'message': 'This event is not active today'})
            
            session = 'morning'
            if event.has_afternoon_session and now.time() >= event.afternoon_start_time:
                session = 'afternoon'
            
            attendance, created = Attendance.objects.get_or_create(
                event=event,
                student=student,
                session=session
            )
            
            if created:
                return JsonResponse({'success': True, 'message': 'You successfully timed in today!'})
            else:
                return JsonResponse({'success': False, 'message': 'You have already timed in for this session'})
        
        except Event.DoesNotExist:
            try:
                special_event = SpecialEvent.objects.get(qr_data=qr_data)
                student = request.user.student
                
                attendance, created = SpecialEventAttendance.objects.get_or_create(
                    special_event=special_event,
                    student=student
                )
                
                if created:
                    return JsonResponse({'success': True, 'message': 'You successfully timed in today!'})
                else:
                    return JsonResponse({'success': False, 'message': 'You have already timed in for this event'})
            except SpecialEvent.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Invalid QR code'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def student_profile(request):
    if request.user.user_type != 'student':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    student = request.user.student
    
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully')
            return redirect('student_profile')
    else:
        form = StudentProfileForm(instance=student)
    
    return render(request, 'student/profile.html', {'form': form, 'student': student})


@login_required
def student_change_password(request):
    if request.user.user_type != 'student':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = StudentPasswordForm(request.POST)
        if form.is_valid():
            current_password = form.cleaned_data['current_password']
            new_password = form.cleaned_data['new_password']
            
            if request.user.check_password(current_password):
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully')
                return redirect('student_profile')
            else:
                messages.error(request, 'Current password is incorrect')
    else:
        form = StudentPasswordForm()
    
    return render(request, 'student/change_password.html', {'form': form})


@login_required
def manage_pos(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    pos_accounts = POSAccount.objects.all()
    return render(request, 'admin/manage_pos.html', {'pos_accounts': pos_accounts})


@login_required
def add_pos(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = POSAccountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'POS account created successfully')
            return redirect('manage_pos')
    else:
        form = POSAccountForm()
    
    return render(request, 'admin/add_pos.html', {'form': form})


@login_required
def delete_pos(request, pos_id):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    pos = get_object_or_404(POSAccount, id=pos_id)
    if request.method == 'POST':
        pos.user.delete()
        messages.success(request, 'POS account deleted successfully')
    
    return redirect('manage_pos')


@login_required
def manage_special_events(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    special_events = SpecialEvent.objects.all().order_by('-start_date')
    return render(request, 'admin/manage_special_events.html', {'special_events': special_events})


@login_required
def add_special_event(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = SpecialEventForm(request.POST, request.FILES)
        if form.is_valid():
            special_event = form.save(commit=False)
            special_event.created_by = request.user
            special_event.save()
            form.save_m2m()
            messages.success(request, 'Special event created successfully')
            return redirect('manage_special_events')
    else:
        form = SpecialEventForm()
    
    return render(request, 'admin/add_special_event.html', {'form': form})


@login_required
def delete_special_event(request, event_id):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    special_event = get_object_or_404(SpecialEvent, id=event_id)
    if request.method == 'POST':
        special_event.delete()
        messages.success(request, 'Special event deleted successfully')
    
    return redirect('manage_special_events')


@login_required
def admin_settings(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings updated successfully')
            return redirect('admin_settings')
    else:
        form = SystemSettingsForm(instance=settings)
    
    return render(request, 'admin/settings.html', {'form': form, 'settings': settings})


@login_required
def admin_change_password(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AdminPasswordChangeForm(request.POST)
        if form.is_valid():
            current_password = form.cleaned_data['current_password']
            new_password = form.cleaned_data['new_password']
            
            if request.user.check_password(current_password):
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully')
                return redirect('admin_settings')
            else:
                messages.error(request, 'Current password is incorrect')
    else:
        form = AdminPasswordChangeForm()
    
    return render(request, 'admin/change_password.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('login')
