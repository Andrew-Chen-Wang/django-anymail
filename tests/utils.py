# Anymail test utils
import sys

import os
import re
import warnings
from base64 import b64decode
from contextlib import contextmanager

from django.test import Client


def decode_att(att):
    """Returns the original data from base64-encoded attachment content"""
    return b64decode(att.encode('ascii'))


SAMPLE_IMAGE_FILENAME = "sample_image.png"


def sample_image_path(filename=SAMPLE_IMAGE_FILENAME):
    """Returns path to an actual image file in the tests directory"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(test_dir, filename)
    return path


def sample_image_content(filename=SAMPLE_IMAGE_FILENAME):
    """Returns contents of an actual image file from the tests directory"""
    filename = sample_image_path(filename)
    with open(filename, "rb") as f:
        return f.read()


# noinspection PyUnresolvedReferences
class AnymailTestMixin:
    """Helpful additional methods for Anymail tests"""

    def assertWarns(self, expected_warning, msg=None):
        # We only support the context-manager version
        try:
            return super(AnymailTestMixin, self).assertWarns(expected_warning, msg=msg)
        except TypeError:
            # Python 2.x: use our backported assertWarns
            return _AssertWarnsContext(expected_warning, self, msg=msg)

    def assertWarnsRegex(self, expected_warning, expected_regex, msg=None):
        # We only support the context-manager version
        try:
            return super(AnymailTestMixin, self).assertWarnsRegex(expected_warning, expected_regex, msg=msg)
        except TypeError:
            # Python 2.x: use our backported assertWarns
            return _AssertWarnsContext(expected_warning, self, expected_regex=expected_regex, msg=msg)

    @contextmanager
    def assertDoesNotWarn(self, disallowed_warning=Warning):
        """Makes test error (rather than fail) if disallowed_warning occurs.

        Note: you probably want to be more specific than the default
        disallowed_warning=Warning, which errors for any warning
        (including DeprecationWarnings).
        """
        try:
            warnings.simplefilter("error", disallowed_warning)
            yield
        finally:
            warnings.resetwarnings()

    def assertCountEqual(self, *args, **kwargs):
        try:
            return super(AnymailTestMixin, self).assertCountEqual(*args, **kwargs)
        except TypeError:
            return self.assertItemsEqual(*args, **kwargs)  # Python 2

    def assertRaisesRegex(self, *args, **kwargs):
        try:
            return super(AnymailTestMixin, self).assertRaisesRegex(*args, **kwargs)
        except TypeError:
            return self.assertRaisesRegexp(*args, **kwargs)  # Python 2

    def assertRegex(self, *args, **kwargs):
        try:
            return super(AnymailTestMixin, self).assertRegex(*args, **kwargs)
        except TypeError:
            return self.assertRegexpMatches(*args, **kwargs)  # Python 2


# Backported from python 3.5
class _AssertWarnsContext(object):
    """A context manager used to implement TestCase.assertWarns* methods."""

    def __init__(self, expected, test_case, expected_regex=None, msg=None):
        self.test_case = test_case
        self.expected = expected
        self.test_case = test_case
        if expected_regex is not None:
            expected_regex = re.compile(expected_regex)
        self.expected_regex = expected_regex
        self.msg = msg

    def _raiseFailure(self, standardMsg):
        # msg = self.test_case._formatMessage(self.msg, standardMsg)
        msg = self.msg or standardMsg
        raise self.test_case.failureException(msg)

    def __enter__(self):
        # The __warningregistry__'s need to be in a pristine state for tests
        # to work properly.
        for v in sys.modules.values():
            if getattr(v, '__warningregistry__', None):
                v.__warningregistry__ = {}
        self.warnings_manager = warnings.catch_warnings(record=True)
        self.warnings = self.warnings_manager.__enter__()
        warnings.simplefilter("always", self.expected)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.warnings_manager.__exit__(exc_type, exc_value, tb)
        if exc_type is not None:
            # let unexpected exceptions pass through
            return
        try:
            exc_name = self.expected.__name__
        except AttributeError:
            exc_name = str(self.expected)
        first_matching = None
        for m in self.warnings:
            w = m.message
            if not isinstance(w, self.expected):
                continue
            if first_matching is None:
                first_matching = w
            if (self.expected_regex is not None and
                not self.expected_regex.search(str(w))):
                continue
            # store warning for later retrieval
            self.warning = w
            self.filename = m.filename
            self.lineno = m.lineno
            return
        # Now we simply try to choose a helpful failure message
        if first_matching is not None:
            self._raiseFailure('"{}" does not match "{}"'.format(
                     self.expected_regex.pattern, str(first_matching)))
        self._raiseFailure("{} not triggered".format(exc_name))


class ClientWithCsrfChecks(Client):
    """Django test Client that enforces CSRF checks

    https://docs.djangoproject.com/en/1.9/ref/csrf/#testing
    """

    def __init__(self, **defaults):
        super(ClientWithCsrfChecks, self).__init__(
            enforce_csrf_checks=True, **defaults)
