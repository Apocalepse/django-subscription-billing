================================
Django app for pay subscriptions
================================

Django application for organizing a pay subscription. It is able to deduct periodic payments from users accounts,
to disconnect at the end of the subscription funds and enable subscription when the money arrives.

Requirments
-----------
celery
django-celery

Installation
------------
    pip install git+https://github.com/Apocalepse/django-subscription-billing.git

1. Add "subscription" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = (
        ...
        'subscription',
    )

2. Run ``python manage.py migrate`` to create the subscription models.

Setup
-----
First, you need to add custom field to your user model to store balance. This field must be ``DecimalField``
with  ``max_digits=8`` and  ``decimal_places=2``.
Example:

    balance = models.DecimalField(u'Balance', max_digits=8, decimal_places=2, default=0)

SUBSCRIPTION_SUBSCRIBER_MODEL — your user model in format ``app.Model``, default is ``auth.User``

SUBSCRIPTION_SUBSCRIBER_MODEL_FIELD — field in model, specified in SUBSCRIPTION_SUBSCRIBER_MODEL, to store balance.
Default is ``account_balance``

SUBSCRIPTION_SUBSCRIBER_KWARGS — default kwargs for filter accounts (example active, boolean field),
default is ``{'is_active': True}``

Usage
-----
Application has 2 task for celery:
1 . make_minus_transactions
Calculating periodic payments for all active subscriptions, creates transactions and disable subscriptions, if need.
Must be run at least once a day.

2. calculate_balances
The task calculates the user's balance, turning over all transactions.
This task also activates the subscription (in the processing of the transaction plus a negative balance in the former,
if enough funds on balance).
Can run as often, how fast you want to adjust the balance and to "see" plus-transaction. For example, every 5 minutes.

Application makes "minus" transactions, plus transactions can be created in code or admin interface.



Create the subscription plan or plans in admin interface.

Application has models for:

Subscription plans,

How you can support this app
----------------------------
Help with documentation, english comments in code and testing. This is something that I do not normally have time to do.
I would appreciate any help and contribution to the project.

