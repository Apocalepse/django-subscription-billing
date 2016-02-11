# -*- coding: utf-8 -*-
from django import forms
from django.contrib import admin
from subscription.models import *
from subscription.settings import PERIOD_CHOICES, PAYMENT_PERIOD_CHOICES


class SubscriptionPlanForm(forms.ModelForm):

    class Meta:
        model = SubscriptionPlan
        fields = '__all__'

    def clean_payment_period(self):
        cd = self.cleaned_data
        period_list = [choice[0] for choice in PERIOD_CHOICES]
        payment_period_list = [choice[0] for choice in PAYMENT_PERIOD_CHOICES]

        if payment_period_list.index(cd['payment_period']) > period_list.index(cd['period']):
            raise forms.ValidationError(u'Период списаний не может быть больше чем срок подписки')
        else:
            return cd['payment_period']


class SubscriptionPlanGroupAdmin(admin.ModelAdmin):
    list_display = ['slug', 'title', 'description']
    list_display_links = ['slug', 'title']


class SubscriptionPlanSubGroupAdmin(admin.ModelAdmin):
    list_display = ['position', 'show_on_site', 'title', 'site_title', 'slug', 'description']
    list_display_links = ['title']
    list_editable = ['position', 'show_on_site']


class PlanVariableInline(admin.TabularInline):
    model = PlanVariable
    extra = 0


class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'group', 'subgroup', 'plan_type', 'period', 'price']
    list_editable = ['group', 'subgroup']
    fieldsets = (
        (u'Технические данные', {'fields': ('group', 'slug')}),
        (u'Описание', {'fields': ('title', 'site_title', 'description_small', 'description')}),
        (u'Настройки', {'fields': (
            'plan_type',
            'price',
            'period',
            'payment_period',
            'free_days',
            'disable_on_minus',
            'enable_on_plus'
        )}),
    )
    list_display_links = ['title']
    list_filter = ['plan_type', 'subgroup', 'group']
    search_fields = ['title', 'description', 'description_small']
    inlines = [PlanVariableInline]

    form = SubscriptionPlanForm


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['plan', 'account', 'active', 'deleted', 'added_date', 'admin_payment_day', 'periodic_payment']
    list_filter = ['active', 'plan', 'plan__plan_type', 'plan__payment_period']
    fields = (
        'active',
        'deleted',
        'plan',
        'account',
        'active_trial',
        # 'added_date',
    )

    def get_queryset(self, request):
        return Subscription.all_objects.all()


class SubscriptionTransactionAdmin(admin.ModelAdmin):
    list_display = ['type', 'amount', 'account', 'subscription', 'description', 'added_date']
    date_hierarchy = 'added_date'
    list_display_links = ['type', 'amount']
    list_filter = ['type', 'subscription__plan__plan_type', 'subscription__plan__payment_period']
    raw_id_fields = ['subscription', 'account']


admin.site.register(SubscriptionPlanGroup, SubscriptionPlanGroupAdmin)
admin.site.register(SubscriptionPlanSubGroup, SubscriptionPlanSubGroupAdmin)

admin.site.register(SubscriptionPlan, SubscriptionPlanAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(SubscriptionTransaction, SubscriptionTransactionAdmin)
