# -*- coding: utf-8 -*-
from decimal import Decimal
from django.utils.translation import ugettext as _
import datetime
import calendar
from django.utils import timezone
from django.db import models
from subscription.settings import *
from subscription.views import add_months


class SubscriptionPlanGroup(models.Model):
    slug = models.SlugField(_(u'Идентификатор'), unique=True)
    title = models.CharField(_(u'Название'), max_length=255)
    site_title = models.CharField(_(u'Название для сайта'), max_length=255, blank=True)
    description = models.TextField(_(u'Описание'), blank=True)

    class Meta:
        verbose_name_plural = _(u'Группы')
        verbose_name = _(u'Группа')

    def __unicode__(self):
        return self.title

    def get_site_title(self):
        plan_title = self.title
        if self.site_title:
            plan_title = self.site_title

        return plan_title


class SubscriptionPlanSubGroup(models.Model):
    position = models.PositiveIntegerField(_(u'Позиция'), default=0, blank=True)
    title = models.CharField(_(u'Название'), max_length=255)
    slug = models.SlugField(_(u'Необязательный идентификатор'), blank=True)
    site_title = models.CharField(_(u'Название для сайта'), max_length=255, blank=True)
    show_on_site = models.BooleanField(_(u'Показывать на сайте'), blank=True, default=True)
    description = models.TextField(_(u'Описание'), blank=True)

    class Meta:
        verbose_name_plural = _(u'Подгруппы')
        verbose_name = _(u'Подгруппа')
        ordering = ['position', '-pk']

    def __unicode__(self):
        return self.title

    def get_site_title(self):
        plan_title = self.title
        if self.site_title:
            plan_title = self.site_title

        return plan_title


class SubscriptionPlan(models.Model):
    slug = models.SlugField(_(u'Уникальный идентификатор'), unique=True, blank=True)
    title = models.CharField(_(u'Название'), max_length=255)
    site_title = models.CharField(_(u'Название для сайта'), max_length=255, blank=True)
    group = models.ForeignKey(SubscriptionPlanGroup, verbose_name=_(u'Группа'), blank=True, null=True,
                              related_name='planes')
    subgroup = models.ForeignKey(SubscriptionPlanSubGroup, verbose_name=_(u'Подгруппа'), blank=True, null=True,
                                 related_name='planes')
    description_small = models.TextField(_(u'Краткое описание'))
    description = models.TextField(_(u'Описание'))
    plan_type = models.CharField(_(u'Тип'), choices=PLAN_CHOICES, max_length=50, default='periodic')
    price = models.DecimalField(_(u'Цена'), max_digits=8, decimal_places=2)
    disable_on_minus = models.BooleanField(_(u'Отключать при 0 или отрицательном балансе'), default=True, blank=True)
    enable_on_plus = models.BooleanField(_(u'Возобновлять при достаточном балансе'), default=True, blank=True)

    period = models.CharField(_(u'Срок подписки'), choices=PERIOD_CHOICES, max_length=50, blank=True)
    payment_period = models.CharField(_(u'Период списаний'), choices=PAYMENT_PERIOD_CHOICES, max_length=50, blank=True)

    free_days = models.PositiveIntegerField(_(u'Бесплатный период (дн.)'), blank=True, null=True,
                                            help_text=_(u'В течение этого периода со дня подписки плата списываться не будет'))
    added_date = models.DateTimeField(_(u'Дата создания'), auto_now_add=True)

    class Meta:
        verbose_name_plural = _(u'Планы подписки')
        verbose_name = _(u'План подписки')
        ordering = ['-price']

    def __unicode__(self):
        return self.title

    def get_site_title(self):
        plan_title = self.title
        if self.site_title:
            plan_title = self.site_title

        return plan_title


class NotDeletedSubscriptionManager(models.Manager):
    def get_queryset(self):
        return super(NotDeletedSubscriptionManager, self).get_queryset().filter(deleted=False)


class Subscription(models.Model):
    active = models.BooleanField(_(u'Активна'), default=True, blank=True)
    deleted = models.BooleanField(_(u'Удалена'), default=False, blank=True)
    plan = models.ForeignKey(SubscriptionPlan, verbose_name=_(u'План'))
    account = models.ForeignKey(SUBSCRIBER_MODEL, verbose_name=_(u'Подписчик'), related_name='subscriptions')
    active_trial = models.BooleanField(_(u'Использовать бесплатный период'), blank=True, default=False,
                                       help_text=_(u'Если активно, подписка не будет списывать средства в течение бесплатного периода плана подписки.'))
    added_date = models.DateTimeField(_(u'Дата создания'), auto_now_add=True, editable=True)
    # added_date.editable = True

    objects = NotDeletedSubscriptionManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name_plural = _(u'Подписки')
        verbose_name = _(u'Подписка')
        ordering = ['-active', '-added_date']

    def __unicode__(self):
        return _(u'%s на %s') % (self.account.__unicode__(), self.plan.title,)

    def payment_start_date(self):
        """
        Дата начала оплаты (тарификации).
        Либо дата создания подписки, либо дата создания + триальный период
        @return:

        """

        payment_start_date = self.added_date

        if self.plan.free_days and self.active_trial:
            payment_start_date += datetime.timedelta(days=self.plan.free_days)

        return payment_start_date

    def payment_date(self):
        """
        День списания средств со счета.
        Это либо день подключения либо день последнего платежа + период аодписки
        """

        today = timezone.now()

        try:
            latest_pay = SubscriptionTransaction.objects.filter(
                type='minus',
                subscription=self,
                added_date__year=today.year
            ).order_by('-added_date')[:1].get()
            payment_start_date = latest_pay.added_date
        except:
            payment_start_date = self.added_date

        if self.plan.payment_period == 'monthly':
            return add_months(payment_start_date, 1)
        elif self.plan.payment_period == 'three_months':
            return add_months(payment_start_date, 3)
        elif self.plan.payment_period == 'half-year':
            return add_months(payment_start_date, 6)
        elif self.plan.payment_period == 'yearly':
            return add_months(payment_start_date, 12)

    def admin_payment_day(self):
        if self.payment_date():
            return self.payment_date().strftime('%d %B')
        else:
            return _(u'Ежедневный платеж')

    admin_payment_day.short_description = _(u'Дата платежа')
    admin_payment_day.allow_tags = True

    def periodic_payment(self):
        """
        Вычисляем ежедневный платеж
        Если подписка не с ежедневным платежом, возвращает цену подписки
        """
        today = timezone.localtime(timezone.now())

        transaction_amount = 0
        if self.plan.payment_period == 'everyday':
            if self.plan.period == 'everyday':
                transaction_amount = self.plan.price
            # Если срок подписки 1 месяц, вычисляем платеж исходя из количества дней в текущем месяце
            elif self.plan.period == 'monthly':
                days_in_month = calendar.monthrange(today.year, today.month)
                days_in_month = days_in_month[1]
                transaction_amount = self.plan.price / days_in_month
            # Если срок подписки 3 месяца, делим стоимость подписки на 3 дальше так же. Далее по аналогии.
            elif self.plan.period == 'three_months':
                days_in_month = calendar.monthrange(today.year, today.month)
                days_in_month = days_in_month[1]
                transaction_amount = self.plan.price / 3 / days_in_month
            elif self.plan.period == 'half-year':
                days_in_month = calendar.monthrange(today.year, today.month)
                days_in_month = days_in_month[1]
                transaction_amount = self.plan.price / 6 / days_in_month
            elif self.plan.period == 'yearly':
                days_in_month = calendar.monthrange(today.year, today.month)
                days_in_month = days_in_month[1]
                transaction_amount = self.plan.price / 12 / days_in_month
        else:
            transaction_amount = self.plan.price

        return transaction_amount.quantize(Decimal('.00'))

    periodic_payment.short_description = _(u'Сумма платежа')
    periodic_payment.allow_tags = True

    def is_free_period(self):
        """
        используется ли сейчас триальный период по данной подписке
        @return: Boolean
        """
        today = timezone.now()

        if self.active_trial and today <= self.payment_start_date():
            return True
        else:
            return False

    def left_free_days(self):
        """
        Сколько осталось бесплатного периода
        @return: Int
        """
        # TODO разобраться +1 или нет
        today = timezone.now()

        if self.is_free_period():
            if self.payment_start_date().date() > today.date():
                delta = self.payment_start_date() - today
                return delta.days + 1
            else:
                return 0
        else:
            return 0


class SubscriptionTransaction(models.Model):
    type = models.CharField(_(u'Тип'), max_length=50, choices=TRANSACTON_TYPE_CHOICES)
    amount = models.DecimalField(_(u'Сумма'), max_digits=8, decimal_places=2)
    subscription = models.ForeignKey(Subscription, verbose_name=_(u'Подписка'), blank=True, null=True, related_name='stransactions')
    account = models.ForeignKey(SUBSCRIBER_MODEL, verbose_name=_(u'Подписчик'), related_name='stransactions')
    promo = models.BooleanField(_(u'Промо-транзакция'), default=False)
    added_date = models.DateTimeField(_(u'Время транзакции'), auto_now_add=True)
    description = models.TextField(_(u'Комментарий'), blank=True)

    class Meta:
        verbose_name = _(u'Транзакция подписки')
        verbose_name_plural = _(u'Транзакции подписок')
        ordering = ('-added_date',)

    def __unicode__(self):
        if self.account:
            recipient = self.account.__unicode__()
        elif self.subscription:
            recipient = self.subscription.account.__unicode__()
        else:
            recipient = u''

        return u'%s %s %s' % (recipient, self.type, self.amount,)


class PlanVariable(models.Model):
    plan = models.ForeignKey(SubscriptionPlan, verbose_name=_(u'План подписки'), related_name='variables')
    slug = models.SlugField(_(u'Идентификатор'), help_text=_(u'Должен быть уникальным в рамках плана'))
    title = models.CharField(_(u'Название'), max_length=255)
    value = models.CharField(_(u'Значение'), max_length=255)

    def __unicode__(self):
        return u'%s: %s' % (self.slug, self.value,)

    class Meta:
        verbose_name_plural = _(u'Переменные')
        verbose_name = _(u'Переменная')

        unique_together = ('plan', 'slug',)
