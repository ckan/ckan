from __future__ import annotations

import time
from typing import Optional

from http import HTTPStatus
import hashlib
import re
from flask.wrappers import Response

from ckan import plugins as p


from ckan.plugins.toolkit import request, config, g, current_user


import logging

log = logging.getLogger(__name__)


class ETagsPlugin(p.SingletonPlugin):
    """ This plugin is to generate 'Strong' etag hashes """

    p.implements(p.IMiddleware)

    # IMiddleware

    def set_etag_for_response(self, response: Response) -> Optional[Response]:
        """Set ETag and return 304 if content is unchanged."""

        __timer = time.time()
        # skip stremaing content
        if not response.is_streamed:
            allowed_status_codes = {HTTPStatus.OK,  # 200
                                    HTTPStatus.MOVED_PERMANENTLY,  # 301
                                    HTTPStatus.FOUND,  # 302
                                    HTTPStatus.UNAUTHORIZED,  # 401
                                    HTTPStatus.FORBIDDEN,  # 403
                                    HTTPStatus.NOT_FOUND  # 404
                                    }

            if response.status_code in allowed_status_codes:
                if 'etag' not in response.headers:
                    # s3 etag uses md5, so using it here also
                    content_type = response.mimetype or ''
                    allowed_types = {'text/plain', 'text/css',
                                     'text/html', 'application/json'}
                    etag_super_strong = u'__etag_super_strong__' in request.environ

                    try:
                        # anon/public get ignored csrf
                        if (etag_super_strong
                                or content_type not in allowed_types
                                or current_user.is_authenticated or g.user):
                            log.debug("not regex-ing payload")
                            data_to_hash = response.get_data()
                        else:
                            log.debug("regex-ing payload for etag")
                            # Regex for both _csrf_token content and csp nonce and don't
                            # care if there is new lines spacing etc attributes which
                            # are dynamic on pages
                            # May need to add more when we come across them.

                            field_name = re.escape(config.get("WTF_CSRF_FIELD_NAME", "_csrf_token"))  # noqa: E501
                            # csrf meta only, if to include value,
                            #   update (?:content) to (?:content|value)
                            pattern = fr'(?i)((?:_csrf_token|{field_name})[^>]*?\b(?:content)=|\bnonce=)["\'][^"\']+(["\'])'  # noqa: E501

                            # Replace values with etag_removed
                            response_data = re.sub(pattern,
                                                   lambda m: m.group(1) + '="etag_removed"',  # noqa: E501
                                                   response.get_data(as_text=True))
                            data_to_hash = response_data.encode()

                        etag = hashlib.md5(data_to_hash).hexdigest()

                        r_time = time.time() - __timer
                        log.debug(' %s %s hash time %.3f seconds',
                                  etag, response.content_length, r_time)

                        response.set_etag(etag)
                    except (AttributeError, IndexError, TypeError,
                            UnicodeEncodeError, ValueError, re.error) as e:
                        r_time = time.time() - __timer
                        logging.info("Failed to compute and set ETag %.3f seconds: %s",
                                     r_time, e)

                etag_not_conditional = (u'__etag_not_conditional__'
                                        not in request.environ)
                if etag_not_conditional:
                    # Use built-in function now that we have an eTag
                    response.make_conditional(request.environ)

        return response
