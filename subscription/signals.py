# -*- coding: utf-8 -*-
from django.dispatch import Signal


# Сигнал отправляется при блокировке подписки
account_blocked = Signal(providing_args=['subscription'])


# Сигнал отправляется при блокировке подписки в случае когда закончился бесплатный период
trial_expired = Signal(providing_args=['subscription'])


# Сигнал отправляется при разблокировке подписки
account_unblocked = Signal(providing_args=['subscription'])
