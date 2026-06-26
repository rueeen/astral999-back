from django.contrib import admin

from .models import TarotCard


@admin.register(TarotCard)
class TarotCardAdmin(admin.ModelAdmin):
    list_display = ('name', 'arcana', 'number', 'created_at')
    list_filter = ('arcana',)
    search_fields = ('name', 'slug', 'keywords')
    prepopulated_fields = {'slug': ('name',)}
