# -*- coding: utf-8 -*-
from operator import itemgetter
from django.utils import timezone
from celery.task import periodic_task
from celery.schedules import crontab
from django.db.models.loading import get_model
from django.db.models import Sum
from subscription import signals
from subscription.settings import *
from subscription.models import Subscription, SubscriptionTransaction


# @periodic_task(run_every=crontab(minute='*/2'))
@periodic_task(run_every=crontab(minute=0, hour=23))
def make_minus_transactions():
    """
    Вычисляет переодические платежи по подпискам, создает транзакции и отключает подписки.
    Запускать не реже раза в сутки.
    """

    # Получаем все активные подписки на сегодня
    subscriptions = Subscription.objects.prefetch_related('plan', 'account').filter(
        active=True,
        plan__plan_type='periodic'
    )
    today = timezone.now()

    # Перебираем их
    for subscription in subscriptions:

        # region Если списания происходят каждый день
        if subscription.plan.payment_period == 'everyday':

            # Если транзакции на сегодняшний день еще нет
            if not SubscriptionTransaction.objects.filter(
                    type='minus',
                    subscription=subscription,
                    added_date__year=today.year,
                    added_date__month=today.month,
                    added_date__day=today.day
            ).exists() and not subscription.is_free_period():
                # print subscription

                # Получаем текущий баланс подписчика
                account_balance = getattr(subscription.account, SUBSCRIBER_MODEL_FIELD)

                # Если баланс больше нуля, создаем минусовую транзацию
                if account_balance > 0:
                    print subscription
                    print 'balance > 0'
                    SubscriptionTransaction.objects.create(
                        type='minus',
                        amount=subscription.periodic_payment(),
                        subscription=subscription,
                        account=subscription.account,
                        description=u'Ежедневное списание по плану «%s»' % subscription.plan.get_site_title()
                    )

                # Если баланс ноль или меньше
                elif account_balance <= 0:
                    # print 'balance <= 0'
                    # print subscription
                    minus_transactions_count = subscription.stransactions.filter(type='minus').count()
                    # print 'minus_transactions_count=%s' % minus_transactions_count

                    # print '%s == %s' % (today.date(), subscription.payment_start_date())

                    # Если по данной подписке небыло списаний, по ней был активен бесплатный период
                    # и сегодняшняя дата — дата начала списаний
                    if minus_transactions_count == 0 and subscription.active_trial and \
                                    today.date() == subscription.payment_start_date().date():
                        print 'end of trial'
                        subscription.active = False
                        subscription.save()
                        signals.trial_expired.send(sender=None, subscription=subscription)

                    elif subscription.plan.disable_on_minus and not subscription.is_free_period():
                        print 'end of money'
                        subscription.active = False
                        subscription.save()
                        signals.account_blocked.send(sender=None, subscription=subscription)

                # # Если баланс меньше или равно 0 и план следует отключить по настройкам и не идет бесплатный период
                # elif account_balance <= 0 and subscription.plan.disable_on_minus and not subscription.is_free_period():
                #     subscription.active = False
                #     subscription.save()
                #     signals.account_blocked.send(sender=None, subscription=subscription)
                #
                # # Если баланс равен 0 и план следует отключить по настройкам
                # elif account_balance == 0 and subscription.plan.disable_on_minus and \
                #                 today.date() == subscription.payment_start_date() and subscription.is_free_period():
                #     subscription.active = False
                #     subscription.save()
                #     signals.account_blocked.send(sender=None, subscription=subscription)
        # endregion

        # region Если списания не каждый день
        else:
            # Проводим списание если прошла вычисленная дата списания и нет списания в этом году
            if today.date().month >= subscription.payment_date().month and \
                            today.date().day >= subscription.payment_date().day and not \
                    SubscriptionTransaction.objects.filter(
                type='minus',
                subscription=subscription,
                account=subscription.account,
                added_date__year=today.year,
            ).exists():
                SubscriptionTransaction.objects.create(
                    type='minus',
                    amount=subscription.plan.price,
                    subscription=subscription,
                    account=subscription.account,
                    description=u'Списание по плану «%s»' % subscription.plan.get_site_title()
                )
        # endregion


# @periodic_task(run_every=crontab(minute='*/1'))
@periodic_task(run_every=crontab(minute='*/5'))
def calculate_balances():
    """
    Производит корректировку счетов подписчиков исходя из транзакций
    """
    account_model = get_model(*SUBSCRIBER_MODEL.split('.', 1))

    # Получаем список подписчиков
    subscribers = account_model.objects.filter(**SUBSCRIBER_KWARGS)

    for subscriber in subscribers:

        # Получаем ПЛЮСОВЫЕ транзакции, либо они равны 0
        plus_transactions = subscriber.stransactions.filter(type='plus')
        if plus_transactions.exists():
            plus_transactions = plus_transactions.aggregate(Sum('amount'))
            plus_transactions = plus_transactions['amount__sum']
        else:
            plus_transactions = 0

        # Получаем МИНУСОВЫЕ транзакции, либо они равны 0
        minus_transactions = subscriber.stransactions.filter(type='minus')
        if minus_transactions.exists():
            minus_transactions = minus_transactions.aggregate(Sum('amount'))
            minus_transactions = minus_transactions['amount__sum']
        else:
            minus_transactions = 0

        # Если плюсовых транзакций вообще нет, значит и баланс равен 0
        if plus_transactions == 0:
            balance = 0

        # Иначе, вычитаем из плюсовых минусовые транзакции
        else:
            balance = plus_transactions - minus_transactions

        # region Включение подписок
        # Если баланс был ноль или меньше, и стал положительный
        # Либо если баланс изменился
        account_balance = getattr(subscriber, SUBSCRIBER_MODEL_FIELD)
        # if account_balance <= 0 and balance > 0:
        # print '---'
        # print account_balance
        # print '='
        # print balance
        # print '---'
        if account_balance != balance:
            # print 'activate!'

            # Находим подписки, которые следует продлить
            need_to_enable_subscription_set = subscriber.subscriptions.filter(
                active=False,
                deleted=False,
                plan__enable_on_plus=True,
                plan__plan_type='periodic'
            )
            # print need_to_enable_subscription_set

            # Теперь находим те, которые можем продлить, по платежу, первым ставим подписку с самым большим платежом
            unsorted_can_to_enable_subscription_set = []
            balance_for_calculation = balance
            for subscription in need_to_enable_subscription_set:
                if balance_for_calculation >= subscription.periodic_payment():
                    unsorted_can_to_enable_subscription_set.append({
                        'subscription': subscription,
                        'periodic_payment': subscription.periodic_payment()
                    })
                    balance_for_calculation -= subscription.periodic_payment()
            sorted_can_to_enable_subscription_set = sorted(unsorted_can_to_enable_subscription_set, key=itemgetter('periodic_payment'), reverse=True)

            # print sorted_can_to_enable_subscription_set

            for subscription_to_enable in sorted_can_to_enable_subscription_set:
                subscription_to_enable['subscription'].active = True

                # Активируем подписку
                subscription_to_enable['subscription'].save()
                signals.account_unblocked.send(sender=None, subscription=subscription_to_enable['subscription'])

                # Сразу создаем транзакцию для списания средств по активированной подписке
                SubscriptionTransaction.objects.create(
                    type='minus',
                    amount=subscription_to_enable['subscription'].periodic_payment(),
                    subscription=subscription_to_enable['subscription'],
                    account=subscription_to_enable['subscription'].account,
                    description=u'Подключение тарифного плана у «%s»' %
                                subscription_to_enable['subscription'].plan.get_site_title()
                )

                # Вызываем пересчет баланса
                calculate_balances.apply_async()

        # endregion

        # Обновляем у подписчика текущий баланс
        update_kwargs = {SUBSCRIBER_MODEL_FIELD: balance}
        account_model.objects.select_for_update().filter(pk=subscriber.pk).update(**update_kwargs)
