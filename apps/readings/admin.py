from django.contrib import admin

from .models import ModelPricing, Reading


@admin.register(ModelPricing)
class ModelPricingAdmin(admin.ModelAdmin):
    list_display = ('model', 'effective_from', 'input_price_per_million', 'output_price_per_million', 'currency')
    list_filter = ('currency',)
    search_fields = ('model',)


@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ('user', 'spread', 'mode', 'status', 'cost', 'cost_currency', 'created_at')
    list_filter = ('spread', 'mode', 'status', 'is_favorite', 'created_at')
    search_fields = ('user__username', 'question', 'ai_response')
