# encoding: utf-8
from __future__ import annotations

import six
import re
import logging

from typing import Any, Iterable, Optional, Dict
from typing_extensions import Literal


INSERT_NEW_SECTIONS_BEFORE_SECTION = 'app:main'
log = logging.getLogger(__name__)


def config_edit_using_option_strings(config_filepath: str,
                                     desired_option_strings: list[str],
                                     section: str,
                                     edit: bool = False) -> None:
    '''Writes the desired_option_strings to the config file.'''
    # Parse the desired_options
    desired_options = list(filter(
        None,
        [parse_option_string(
            section, desired_option_string, raise_on_error=True)
         for desired_option_string in desired_option_strings]))
    # Make the changes
    config_edit(config_filepath, desired_options, edit=edit)


def config_edit_using_merge_file(config_filepath: str,
                                 merge_config_filepath: str) -> None:
    '''Merges options found in a config file (merge_config_filepath) into the
    main config file (config_filepath).
    '''
    # Read and parse the merge config filepath
    with open(merge_config_filepath, 'rb') as f:
        input_lines = [six.ensure_str(line).rstrip('\n') for line in f]
    desired_options_dict = parse_config(input_lines)
    desired_options = desired_options_dict.values()
    # Make the changes
    config_edit(config_filepath, desired_options)


def config_edit(config_filepath: str,
                desired_options: Iterable['Option'],
                edit: bool = False) -> None:
    '''Writes the desired_options to the config file.'''
    # Read and parse the existing config file
    with open(config_filepath, 'rb') as f:
        input_lines = [six.ensure_str(line).rstrip('\n') for line in f]
    existing_options_dict = parse_config(input_lines)
    existing_options = existing_options_dict.values()

    # For every desired option, decide what action to take
    new_sections = calculate_new_sections(existing_options, desired_options)
    changes = calculate_changes(existing_options_dict, desired_options, edit)

    # write the file with the changes
    output = make_changes(input_lines, new_sections, changes)
    with open(config_filepath, 'wb') as f:
        f.write(six.ensure_binary('\n'.join(output) + '\n'))


def parse_option_string(section: str,
                        option_string: str,
                        raise_on_error: bool = False) -> Optional['Option']:
    option_match = OPTION_RE.match(option_string)
    if not option_match:
        if raise_on_error:
            raise ConfigToolError('Option did not parse: "%s". Must be: '
                                  '"key = value"' % option_string)
        return None
    is_commented_out, key, value = option_match.group('commentedout',
                                                      'option', 'value')
    key = key.strip()
    value = value.strip()
    return Option(section, key, value, is_commented_out,
                  original=option_string)


class Option(object):
    def __init__(self,
                 section: str,
                 key: str,
                 value: str,
                 is_commented_out: Any,
                 original: Optional[str] = None) -> None:
        self.section = section
        self.key = key
        self.value = value
        self.is_commented_out = bool(is_commented_out)
        self.original = original

    def __repr__(self):
        return '<Option [%s] %s>' % (self.section, self)

    def __str__(self):
        if self.original:
            return self.original
        return '%s%s = %s' % ('#' if self.is_commented_out else '',
                              self.key, self.value)

    @property
    def id(self):
        return '%s-%s' % (self.section, self.key)

    def comment_out(self) -> None:
        self.is_commented_out = True
        self.original = None  # it is no longer accurate


def calculate_new_sections(existing_options: Iterable[Option],
                           desired_options: Iterable[Option]) -> set[str]:
    existing_sections = {option.section for option in existing_options}
    desired_sections = {option.section for option in desired_options}
    new_sections = desired_sections - existing_sections
    return new_sections


class Changes(Dict[str, Any]):
    '''A store of Options that are to "edit" or "add" to existing sections of a
       config file. (Excludes options that go into new sections.)'''
    def add(self, action: Literal["edit", "add"], option: Option) -> None:
        assert action in ('edit', 'add')
        assert isinstance(option, Option)
        if option.section not in self:
            self[option.section] = {}
        if not self[option.section].get(action):
            self[option.section][action] = []
        self[option.section][action].append(option)

    def get(self, section: str, action: Optional[str] = None) -> list[Option]:
        try:
            return self[section][action]
        except KeyError:
            return []


def calculate_changes(existing_options_dict: dict[str, Any],
                      desired_options: Iterable[Option],
                      edit: bool) -> Changes:
    changes = Changes()

    for desired_option in desired_options:
        action: Literal['add', 'edit'] = 'edit' if desired_option.id\
            in existing_options_dict else 'add'
        if edit and action != 'edit':
            raise ConfigToolError(
                'Key "%s" does not exist in section "%s"' %
                (desired_option.key, desired_option.section))
        changes.add(action, desired_option)
    return changes


def parse_config(input_lines: list[str]) -> dict[str, Option]:
    '''
    Returns a dict of Option objects, keyed by Option.id, given the lines in a
    config file.
    (Not using ConfigParser.set() as it does not store all the comments and
    ordering)
    '''
    section = 'app:main'  # default (for merge config files)
    options = {}
    for line in input_lines:
        # ignore blank lines
        if line.strip() == '':
            continue
        # section heading
        section_match = SECTION_RE.match(line)
        if section_match:
            section = section_match.group('header')
            continue
        # option
        option = parse_option_string(section, line)
        if option:
            options[option.id] = option
    return options


def make_changes(input_lines: Iterable[str], new_sections: Iterable[str],
                 changes: Changes) -> list[str]:
    '''Makes changes to the config file (returned as lines).'''
    output: list[str] = []
    section = None
    options_to_edit_in_this_section = {}  # key: option
    options_already_edited = set()
    have_inserted_new_sections = False

    def write_option(option: Any):
        output.append(str(option))

    def insert_new_sections(new_sections: Iterable[str]):
        for section in new_sections:
            output.append('[%s]' % section)
            for option in changes.get(section, 'add'):
                write_option(option)
                log.info('Created option %s = "%s" (NEW section "%s")',
                         option.key, option.value, section)
            write_option('')

    for line in input_lines:
        # leave blank lines alone
        if line.strip() == '':
            output.append(line)
            continue
        section_match = SECTION_RE.match(line)
        if section_match:
            section = section_match.group('header')
            if section == INSERT_NEW_SECTIONS_BEFORE_SECTION:
                # insert new sections here
                insert_new_sections(new_sections)
                have_inserted_new_sections = True
            output.append(line)
            # at start of new section, write the 'add'ed options
            for option in changes.get(section, 'add'):
                write_option(option)
            options_to_edit_in_this_section = {option.key: option
                                               for option
                                               in changes.get(section, 'edit')}
            continue
        existing_option = parse_option_string(
            section, line) if section else None
        if not existing_option:
            # leave alone comments (does not include commented options)
            output.append(line)
            continue
        updated_option = \
            options_to_edit_in_this_section.get(existing_option.key)
        if updated_option:
            changes_made = None
            key = existing_option.key
            if existing_option.id in options_already_edited:
                if not existing_option.is_commented_out:
                    log.info('Commented out repeat of %s (section "%s")',
                             key, section)
                    existing_option.comment_out()
                else:
                    log.info('Left commented out repeat of %s (section "%s")',
                             key, section)
            elif not existing_option.is_commented_out and \
                    updated_option.is_commented_out:
                changes_made = 'Commented out %s (section "%s")' % \
                    (key, section)
            elif existing_option.is_commented_out and \
                    not updated_option.is_commented_out:
                changes_made = 'Option uncommented and set %s = "%s" ' \
                    '(section "%s")' % \
                    (key, updated_option.value, section)
            elif not existing_option.is_commented_out and \
                    not updated_option.is_commented_out:
                if existing_option.value != updated_option.value:
                    changes_made = 'Edited option %s = "%s"->"%s" ' \
                        '(section "%s")' % \
                        (key, existing_option.value,
                         updated_option.value, section)
                else:
                    changes_made = 'Option unchanged %s = "%s" ' \
                        '(section "%s")' % \
                        (key, existing_option.value, section)

            if changes_made:
                log.info(changes_made)
                write_option(updated_option)
                options_already_edited.add(updated_option.id)
            else:
                write_option(existing_option)
        else:
            write_option(existing_option)
    if new_sections and not have_inserted_new_sections:
        # must not have found the INSERT_NEW_SECTIONS_BEFORE_SECTION
        # section so put the new sections at the end
        insert_new_sections(new_sections)

    return output


# Regexes basically the same as in ConfigParser - OPTCRE & SECTCRE
# Expressing them here because they move between Python 2 and 3
OPTION_RE = re.compile(r'(?P<commentedout>[#;]\s*)?'  # custom
                       r'(?P<option>[^:=\s][^:=]*)'
                       r'\s*(?P<vi>[:=])\s*'
                       r'(?P<value>.*)$')
SECTION_RE = re.compile(r'\[(?P<header>.+)\]')


class ConfigToolError(Exception):
    pass
