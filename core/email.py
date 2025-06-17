import base64
import logging
import os
from abc import ABC, abstractmethod
from typing import Union

import requests
import resend
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailInterface(ABC):
    @abstractmethod
    def send_email(
        self,
        subject: str,
        html_template_path: str,
        to_email: Union[str, list[str]],
        context: dict,
        attachments: list = None,
    ) -> None:
        pass


class SmtpEmailService(EmailInterface):
    def send_email(
        self,
        subject: str,
        html_template_path: str,
        to_email: Union[str, list[str]],
        context: dict,
        attachments: list = None,
    ) -> None:
        html_message = render_to_string(html_template_path, context)
        plain_message = strip_tags(html_message)

        # Convert single email to list for consistency
        if isinstance(to_email, str):
            to_email = [to_email]

        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=f"Trendibble <{settings.EMAIL_HOST_USER}>",
            to=to_email,
        )
        email.attach_alternative(html_message, "text/html")

        if attachments:
            for attachment in attachments:
                email.attach_file(attachment)

        email.send()
        logger.info(
            f"Successfully sent email with attachments to {to_email} using SMTP"
        )


class ResendEmailService(EmailInterface):
    def __init__(self):
        self.api_key = settings.RESEND_SMTP_PASSWORD
        self.from_email = settings.RESEND_FROM_EMAIL
        resend.api_key = self.api_key

    def send_email(
        self,
        subject: str,
        html_template_path: str,
        to_email: Union[str, list[str]],
        context: dict,
        attachments: list = None,
    ) -> None:
        html_message = render_to_string(html_template_path, context)
        plain_message = strip_tags(html_message)

        # Convert single email to list for consistency
        if isinstance(to_email, str):
            to_email = [to_email]

        params = {
            "from": self.from_email,
            "to": to_email,
            "subject": subject,
            "html": html_message,
            "text": plain_message,
        }

        if attachments:
            resend_attachments = []
            for attachment_path in attachments:
                with open(attachment_path, "rb") as file:
                    content = file.read()
                    resend_attachments.append(
                        {
                            "filename": os.path.basename(attachment_path),
                            "content": list(content),
                            "content_type": self._get_content_type(attachment_path),
                        }
                    )
            params["attachments"] = resend_attachments

        try:
            email = resend.Emails.send(params)
            logger.info(f"Successfully sent email to {to_email} using Resend API")
            return email
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise

    def _get_content_type(self, file_path):
        # This is a simple implementation. You might want to use a more robust method
        # or a library like python-magic for more accurate content type detection.
        extension = os.path.splitext(file_path)[1].lower()
        content_types = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".txt": "text/plain",
            # Add more mappings as needed
        }
        return content_types.get(extension, "application/octet-stream")


class ZeptoMailEmailService(EmailInterface):
    def __init__(self):
        self.url = "https://api.zeptomail.com/v1.1/email"
        self.api_key = settings.ZEPTOMAIL_API_KEY
        self.from_email = settings.ZEPTOMAIL_FROM_EMAIL
        self.from_name = settings.ZEPTOMAIL_FROM_NAME

    def send_email(
        self,
        subject: str,
        html_template_path: str,
        to_email: Union[str, list[str]],
        context: dict,
        attachments: list = None,
    ) -> None:
        html_message = render_to_string(html_template_path, context)

        # Convert single email to list for consistency
        if isinstance(to_email, str):
            to_email = [to_email]

        payload = {
            "from": {"address": self.from_email, "name": self.from_name},
            "to": [{"email_address": {"address": email}} for email in to_email],
            "subject": subject,
            "htmlbody": html_message,
        }

        # Process attachments if provided
        if attachments:
            payload["attachments"] = []
            for attachment in attachments:
                with open(attachment, "rb") as file:
                    file_content = file.read()
                    encoded_file = base64.b64encode(file_content).decode()
                    file_name = os.path.basename(attachment)
                    mime_type = self._get_mime_type(attachment)

                    payload["attachments"].append(
                        {
                            "content": encoded_file,
                            "name": file_name,
                            "mime_type": mime_type,
                        }
                    )

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Zoho-enczapikey {self.api_key}",
        }

        try:
            response = requests.post(self.url, json=payload, headers=headers)
            response.raise_for_status()  # Raise an error if the request failed
            logger.info(
                f"Successfully sent email with attachments to {to_email} using ZeptoMail"
            )
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Failed to send email with attachments to {to_email}: {str(e)}"
            )
            raise

    def _get_mime_type(self, file_path: str) -> str:
        # You can add more mime types here based on the file extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".jpg" or ext == ".jpeg":
            return "image/jpeg"
        elif ext == ".png":
            return "image/png"
        elif ext == ".pdf":
            return "application/pdf"
        else:
            return "application/octet-stream"  # Default type for other files


class EmailNotificationService:
    """
    Email notification service that uses the email provider specified in Django settings.
    Configure EMAIL_SERVICE_TYPE in your Django settings:

    EMAIL_SERVICE_TYPE = 'smtp'  # or 'resend', 'sendgrid', 'zeptomail'
    """

    DEFAULT_SERVICE = "smtp"
    VALID_SERVICES = {
        "smtp": SmtpEmailService,
        "resend": ResendEmailService,
        "zeptomail": ZeptoMailEmailService,
    }

    def __init__(self):
        service_type = getattr(
            settings, "EMAIL_SERVICE_TYPE", self.DEFAULT_SERVICE
        ).lower()

        if service_type not in self.VALID_SERVICES:
            logger.warning(
                f"Invalid EMAIL_SERVICE_TYPE '{service_type}' in settings. "
                f"Using default service '{self.DEFAULT_SERVICE}'"
            )
            service_type = self.DEFAULT_SERVICE

        self.email_service = self.VALID_SERVICES[service_type]()
        logger.info(
            f"Initialized EmailNotificationService using {service_type} provider"
        )

    def send_email(
        self,
        subject: str,
        html_template_path: str,
        to_email: Union[str, list[str]],
        context: dict,
        attachments: list = None,
    ) -> None:
        self.email_service.send_email(
            subject, html_template_path, to_email, context, attachments
        )
