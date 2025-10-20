from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('', views.unified_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registration/', views.student_registration_check, name='registration_check'),
    path('registration/<str:student_id>/', views.student_registration, name='student_registration'),
    
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('students/', views.manage_students, name='manage_students'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('students/delete/<int:student_id>/', views.delete_student, name='delete_student'),
    path('students/view/<int:student_id>/', views.view_student, name='view_student'),
    path('students/import/', views.import_students_csv, name='import_students'),
    
    path('events/', views.manage_events, name='manage_events'),
    path('events/add/', views.add_event, name='add_event'),
    path('events/edit/<int:event_id>/', views.edit_event, name='edit_event'),
    path('events/delete/<int:event_id>/', views.delete_event, name='delete_event'),
    path('events/qr/<int:event_id>/', views.view_event_qr, name='view_event_qr'),
    
    path('attendance/export/', views.export_attendance, name='export_attendance'),
    path('attendance/scan/', views.scan_qr, name='scan_qr'),
    path('attendance/process/', views.process_attendance, name='process_attendance'),
    
    path('profile/', views.student_profile, name='student_profile'),
    path('profile/change-password/', views.student_change_password, name='student_change_password'),
    
    path('pos/', views.manage_pos, name='manage_pos'),
    path('pos/add/', views.add_pos, name='add_pos'),
    path('pos/delete/<int:pos_id>/', views.delete_pos, name='delete_pos'),
    
    path('special-events/', views.manage_special_events, name='manage_special_events'),
    path('special-events/add/', views.add_special_event, name='add_special_event'),
    path('special-events/delete/<int:event_id>/', views.delete_special_event, name='delete_special_event'),
    path('special-events/edit/<int:event_id>/', views.edit_special_event, name='edit_special_event'),

    path('settings/', views.admin_settings, name='admin_settings'),
    path('settings/change-password/', views.admin_change_password, name='admin_change_password'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)