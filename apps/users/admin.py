from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + ((
        'Perfil',
        {'fields': (
            'bio', 'avatar', 'birth_date', 'birth_time', 'birth_place',
            'plan', 'plan_expires_at',
        )},
    ),)
