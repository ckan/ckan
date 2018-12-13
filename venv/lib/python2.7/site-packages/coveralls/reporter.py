# coding: utf-8
import logging
import os
import sys

from coverage import __version__
from coverage.misc import NoSource
from coverage.misc import NotPython
from coverage.phystokens import source_encoding
from coverage.report import Reporter

from .exception import CoverallsException


log = logging.getLogger('coveralls.reporter')


class CoverallReporter(Reporter):
    """ Custom coverage.py reporter for coveralls.io
    """
    def __init__(self, *args, **kwargs):
        self.source_files = []
        super(CoverallReporter, self).__init__(*args, **kwargs)

    def report(self, morfs=None):
        """ Generate a part of json report for coveralls

        `morfs` is a list of modules or filenames.
        `outfile` is a file object to write the json to.
        """
        units = None
        if hasattr(self, 'find_code_units'):
            self.find_code_units(morfs)
        else:
            units = self.find_file_reporters(morfs)

        if units is None:
            if hasattr(self, 'code_units'):
                units = self.code_units
            else:
                units = self.file_reporters

        for cu in units:
            try:
                analyzed = self.coverage._analyze(cu)  # pylint: disable=W0212
                self.parse_file(cu, analyzed)
            except NoSource:
                if not self.config.ignore_errors:
                    log.warning('No source for %s', cu.filename)
            except NotPython:
                # Only report errors for .py files, and only if we didn't
                # explicitly suppress those errors.
                if cu.should_be_python() and not self.config.ignore_errors:
                    log.warning('Source file is not python %s', cu.filename)
            except KeyError:
                cov3x = __version__[0] < 4
                cov40 = __version__[0] == 4 and __version__[1] < 1
                if cov3x or cov40:
                    raise CoverallsException(
                        'Old (<4.1) versions of coverage.py do not work '
                        'consistently on new versions of Python. Please '
                        'upgrade your coverage.py.'
                    )

                raise

        return self.source_files

    @staticmethod
    def get_hits(line_num, analysis):
        """ Source file stats for each line.

            * A positive integer if the line is covered,
            representing the number of times the line is hit during the test
            suite.
            * 0 if the line is not covered by the test suite.
            * null to indicate the line is not relevant to code coverage
              (it may be whitespace or a comment).
        """
        if line_num in analysis.missing:
            return 0

        if line_num not in analysis.statements:
            return None

        return 1

    @staticmethod
    def get_arcs(analysis):
        """ Hit stats for each branch.

            Returns a flat list where every four values represent a branch:
            1. line-number
            2. block-number (not used)
            3. branch-number
            4. hits (we only get 1/0 from coverage.py)
        """
        if not analysis.has_arcs():
            return None

        branch_lines = analysis.branch_lines()
        branches = []

        for l1, l2 in analysis.arcs_executed():
            if l1 in branch_lines:
                branches.extend((l1, 0, abs(l2), 1))

        for l1, l2 in analysis.arcs_missing():
            if l1 in branch_lines:
                branches.extend((l1, 0, abs(l2), 0))

        return branches

    def parse_file(self, cu, analysis):
        """ Generate data for single file """
        if hasattr(analysis, 'parser'):
            filename = cu.file_locator.relative_filename(cu.filename)
            source_lines = analysis.parser.lines
            with cu.source_file() as source_file:
                source = source_file.read()

            try:
                if sys.version_info < (3, 0):
                    encoding = source_encoding(source)
                    if encoding != 'utf-8':
                        source = source.decode(encoding).encode('utf-8')
            except UnicodeDecodeError:
                log.warning(
                    'Source file %s can not be properly decoded, skipping. '
                    'Please check if encoding declaration is ok',
                    os.path.basename(cu.filename))
                return
        else:
            if hasattr(cu, 'relative_filename'):
                filename = cu.relative_filename()
            else:
                filename = analysis.coverage.file_locator.relative_filename(
                    cu.filename)

            token_lines = analysis.file_reporter.source_token_lines()
            source_lines = list(enumerate(token_lines))
            source = analysis.file_reporter.source()

        coverage_lines = [self.get_hits(i, analysis)
                          for i in range(1, len(source_lines) + 1)]

        # ensure results are properly merged between platforms
        posix_filename = filename.replace(os.path.sep, '/')

        results = {
            'name': posix_filename,
            'source': source,
            'coverage': coverage_lines,
        }

        branches = self.get_arcs(analysis)
        if branches:
            results['branches'] = branches

        self.source_files.append(results)
