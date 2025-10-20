from core.models import SystemSettings


def system_settings(request):
    settings = SystemSettings.get_settings()
    return {
        'system_settings': settings,
    }
