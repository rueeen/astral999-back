from django.contrib import admin

from .models import AnthropicCostReconciliation, ApiTopUp, ModelPricing, Reading, ReadingFeedback


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
