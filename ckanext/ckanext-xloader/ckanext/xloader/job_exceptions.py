# encoding: utf-8

from six import text_type as str


class DataTooBigError(Exception):
    pass


class JobError(Exception):
    pass


class FileCouldNotBeLoadedError(Exception):
    pass


class HTTPError(JobError):
    """Exception that's raised if a job fails due to an HTTP problem."""

    def __init__(self, message, status_code, request_url, response):
        """Initialise a new HTTPError.

        :param message: A human-readable error message
        :type message: string

        :param status_code: The status code of the errored HTTP response,
            e.g. 500
        :type status_code: int

        :param request_url: The URL that was requested
        :type request_url: string

        :param response: The body of the errored HTTP response as unicode
            (if you have a requests.Response object then response.text will
            give you this)
        :type response: unicode

        """
        super(HTTPError, self).__init__(message)
        self.message = message
        self.status_code = status_code
        self.request_url = request_url
        self.response = response

    def __str__(self):
        return str('{} status={} url={} response={}'.format(
            self.message, self.status_code, self.request_url, self.response)
            .encode('ascii', 'replace'))


class LoaderError(JobError):
    '''Exception that's raised if a load fails'''
    pass
