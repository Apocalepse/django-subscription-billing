# coding: utf-8
from django.utils.translation import ugettext as _
from django.conf import settings


SUBSCRIBER_MODEL = getattr(settings, "SUBSCRIPTION_SUBSCRIBER_MODEL", 'auth.User')

SUBSCRIBER_MODEL_FIELD = getattr(settings, "SUBSCRIPTION_SUBSCRIBER_MODEL_FIELD", 'account_balance')

SUBSCRIBER_KWARGS = getattr(settings, "SUBSCRIPTION_SUBSCRIBER_KWARGS", {'is_active': True})

PLAN_CHOICES = getattr(settings, "SUBSCRIPTION_PLAN_CHOICES",
    (
        ('periodic', _(u'Периодический'),),
        ('onetime', _(u'Единоразовый'),),
    )
)

PERIOD_CHOICES = getattr(settings, "SUBSCRIPTION_PERIOD_CHOICES",
    (
        ('everyday', _(u'День'),),
        ('monthly', _(u'Месяц'),),
        ('three_months', _(u'Три месяца'),),
        ('half-year', _(u'Полгода'),),
        ('yearly', _(u'Год'),),
    )
)

PAYMENT_PERIOD_CHOICES = getattr(settings, "SUBSCRIPTION_PERIOD_PAYMENT_PERIOD_CHOICES",
    (
        ('everyday', _(u'Раз в день'),),
        ('monthly', _(u'Раз в месяц'),),
        ('three_months', _(u'Раз три месяца'),),
        ('half-year', _(u'Раз в полгода'),),
        ('yearly', _(u'Раз в год'),),
    )
)

TRANSACTON_TYPE_CHOICES = getattr(settings, "SUBSCRIPTION_TRANSACTON_TYPE_CHOICES",
    (
        ('plus', u'+'),
        ('minus', u'-'),
    )
)
