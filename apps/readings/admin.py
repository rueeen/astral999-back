from django.contrib import admin

from .models import AnthropicCostReconciliation, ApiTopUp, ModelPricing, Reading, ReadingFeedback


@admin.register(ModelPricing)
class ModelPricingAdmin(admin.ModelAdmin):
    list_display = ('model', 'effective_from', 'input_price_per_million', 'output_price_per_million', 'currency')
    list_filter = ('currency',)
    search_fields = ('model',)


@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ('user', 'spread', 'mode', 'feedback_value', 'is_exemplar', 'status', 'cost', 'cost_currency', 'created_at')
    list_filter = ('spread', 'mode', 'feedback__value', 'is_exemplar', 'status', 'is_favorite', 'created_at')
    search_fields = ('user__username', 'question', 'ai_response')
    actions = ('mark_as_exemplar', 'unmark_as_exemplar')
    list_select_related = ('user',)

    @admin.display(description='valoración', ordering='feedback__value')
    def feedback_value(self, obj):
        feedback = next(iter(obj.feedback.all()), None)
        return feedback.get_value_display() if feedback else '—'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('feedback')

    def save_model(self, request, obj, form, change):
        previous_mode = None
        if change:
            previous_mode = Reading.objects.filter(pk=obj.pk).values_list('mode', flat=True).first()
        super().save_model(request, obj, form, change)
        from django.core.cache import cache
        cache.delete_many({f'reading-exemplars:{mode}' for mode in (previous_mode, obj.mode) if mode})

    @admin.action(description='Marcar como ejemplares')
    def mark_as_exemplar(self, request, queryset):
        queryset.update(is_exemplar=True)
        self._clear_exemplar_cache(queryset)

    @admin.action(description='Desmarcar como ejemplares')
    def unmark_as_exemplar(self, request, queryset):
        queryset.update(is_exemplar=False)
        self._clear_exemplar_cache(queryset)

    @staticmethod
    def _clear_exemplar_cache(queryset):
        from django.core.cache import cache
        for mode in queryset.values_list('mode', flat=True).distinct():
            cache.delete(f'reading-exemplars:{mode}')


@admin.register(ReadingFeedback)
class ReadingFeedbackAdmin(admin.ModelAdmin):
    list_display = ('reading', 'user', 'value', 'created_at')
    list_filter = ('value', 'created_at')
    search_fields = ('reading__question', 'user__username', 'comment')
    readonly_fields = ('generation_context', 'created_at')


@admin.register(ApiTopUp)
class ApiTopUpAdmin(admin.ModelAdmin):
    list_display = ('date', 'amount', 'note')
    date_hierarchy = 'date'


@admin.register(AnthropicCostReconciliation)
class AnthropicCostReconciliationAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date', 'reported_cost', 'local_cost', 'difference', 'synced_at')
    readonly_fields = ('start_date', 'end_date', 'reported_cost', 'local_cost', 'difference', 'synced_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
