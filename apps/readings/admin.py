from django.contrib import admin

from .models import Reading


@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ('user', 'spread', 'is_favorite', 'created_at')
    list_filter = ('spread', 'is_favorite', 'created_at')
    search_fields = ('user__username', 'question', 'ai_response')
