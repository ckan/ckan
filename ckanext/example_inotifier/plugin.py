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


class ExampleINotifier2Plugin(plugins.SingletonPlugin):
    plugins.implements(plugins.INotifier, inherit=True)

    def notify_recipient(
        self,
        recipient_name: str,
        recipient_email: str,
        subject: str,
        body: str,
        body_html: Optional[str] = None,
        headers: Optional[dict[str, Any]] = None,
        attachments: Any = None
    ) -> bool:

        msg = (
            f'Notification [2] example for {recipient_name} '
            f'<{recipient_email}> '
            f'with subject {subject} and body {body} or {body_html} '
            f'and headers {headers} and attachments {attachments}'
        )
        log.info(msg)

        # Here you would send an email to the recipient
        return True