"""
Two test notifiers
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from ckan import plugins


log = logging.getLogger(__name__)


class ExampleINotifier1Plugin(plugins.SingletonPlugin):
    plugins.implements(plugins.INotifier, inherit=True)

    def notify_recipient(
        self,
        already_notified: bool,
        recipient_name: str,
        recipient_email: str,
        subject: str,
        body: str,
        body_html: Optional[str] = None,
        headers: Optional[dict[str, Any]] = None,
        attachments: Any = None
    ) -> bool:

        msg = (
            f'Notification [1] example for {recipient_name} '
            f'<{recipient_email}> '
            f'with subject {subject} and body {body} or {body_html} '
            f'and headers {headers} and attachments {attachments}'
        )
        log.info(msg)

        # Here you would send an email to the recipient
        return True

    def notify_about_topic(self,
                           already_notified: bool,
                           topic: str,
                           details: Optional[dict[str, Any]] = None) -> bool:

        user = details.get('user', None) if details else None
        if user:
            msg = (
                f'Notification [1] example for topic {topic} '
                f'({user.name})<{user.email}>'
            )
            log.info(msg)

        # Do any extra processing for specific topics
        return True


class ExampleINotifier2Plugin(plugins.SingletonPlugin):
    plugins.implements(plugins.INotifier, inherit=True)

    def notify_recipient(
        self,
        already_notified: bool,
        recipient_name: str,
        recipient_email: str,
        subject: str,
        body: str,
        body_html: Optional[str] = None,
        headers: Optional[dict[str, Any]] = None,
        attachments: Any = None
    ) -> bool:

        if already_notified:
            # Do not process if another plugin has already
            # handled this notification
            return True

        msg = (
            f'Notification [2] example for {recipient_name} '
            f'<{recipient_email}> '
            f'with subject {subject} and body {body} or {body_html} '
            f'and headers {headers} and attachments {attachments}'
        )
        log.info(msg)

        # Here you would send an email to the recipient
        return True

    def notify_about_topic(self,
                           already_notified: bool,
                           topic: str,
                           details: Optional[dict[str, Any]] = None) -> bool:

        if already_notified:
            # Do not process if another plugin has already handled this topic
            return True

        user = details.get('user', None) if details else None
        if user:
            msg = (
                f'Notification [2] example for topic {topic} '
                f'({user.name})<{user.email}>'
            )
            log.info(msg)

        # Do any extra processing for specific topics
        return True
