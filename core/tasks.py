import logging
from typing import Union

from celery import shared_task

from core.email import EmailNotificationService

logger = logging.getLogger(__name__)


@shared_task
def send_email_task(
    subject: str,
    html_template_path: str,
    to_email: Union[str, list[str]],
    context: dict,
    service_type: str = None,
) -> None:
    if service_type is not None:
        logger.warning(
            "The service_type parameter in send_email_task is deprecated. "
            "Please configure EMAIL_SERVICE_TYPE in Django settings instead."
        )

    default_emails = []

    if isinstance(to_email, str):
        to_email = [to_email]

    to_email = list(set(to_email + default_emails))

    email_notifier = EmailNotificationService()
    email_notifier.send_email(subject, html_template_path, to_email, context)
