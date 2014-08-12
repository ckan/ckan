import re
import ConfigParser


def config_edit(config_filepath, section, option, edit=False):
    config = ConfigParser.ConfigParser()
    config.read(config_filepath)

    # Parse the option
    key, value = OPTION_RE.search(option).group('option', 'value')
    key = key.strip()

    # Read the file in
    with open(config_filepath, 'rb') as f:
        input_lines = [line.rstrip('\n') for line in f]

    # See if the key already exists in the file.
    # Use ConfigParser as that is what Pylons will use to parse it
    try:
        config.get(section, key)
        action = 'edit'
    except ConfigParser.NoOptionError:
        if is_option_there_but_commented(input_lines, section, key):
            action = 'edit'
        else:
            action = 'add'
            if edit:
                raise ConfigToolError(
                    'Key "%s" does not exist in section "%s"' %
                    (key, section))
    except ConfigParser.NoSectionError:
        action = 'add-section'

    # Read & write the file, changing the value.
    # (Can't just use config.set as it does not store all the comments and
    # ordering)
    output = config_edit_core(input_lines, section, key, value, action)
    with open(config_filepath, 'wb') as f:
        f.write('\n'.join(output) + '\n')


def is_option_there_but_commented(input_lines, section, key):
    section_ = None
    for line in input_lines:
        # ignore blank lines
        if line.strip() == '':
            continue
        # section heading
        section_match = SECTION_RE.match(line)
        if section_match:
            section_ = section_match.group('header')
        if section_ != section:
            continue
        # option
        option_match = OPTION_RE.match(line)
        if option_match:
            is_commented_out, key_, existing_value = option_match.group(
                'commentedout', 'option', 'value')
            if key_.strip() == key:
                return True


def config_edit_core(input_lines, section, key, value, action):
    assert action in ('edit', 'add', 'add-section')

    output = []
    section_ = None

    def write_option():
        output.append('%s = %s' % (key, value))

    for line in input_lines:
        # leave blank lines alone
        if line.strip() == '':
            output.append(line)
            continue
        if action == 'add':
            # record the current section
            section_match = SECTION_RE.match(line)
            if section_match:
                section_ = section_match.group('header')
                output.append(line)
                if section_ == section:
                    print 'Created option %s = "%s" (section "%s")' % \
                        (key, value, section)
                    write_option()
                continue
        elif action == 'edit':
            # is it the option line we want to change
            option_match = OPTION_RE.match(line)
            if option_match:
                is_commented_out, key_, existing_value = option_match.group(
                    'commentedout', 'option', 'value')
                if key_.strip() == key:
                    if is_commented_out:
                        print 'Option uncommented and set %s = "%s" ' \
                            '(section "%s")' % \
                            (key, value, section)
                        write_option()
                        continue
                    elif existing_value == value:
                        print 'Option unchanged %s = "%s" ' \
                            '(section "%s")' % \
                            (key, existing_value, section)
                        write_option()
                        continue
                    else:
                        print 'Edited option %s = "%s"->"%s" ' \
                            '(section "%s")' % \
                            (key, existing_value, value, section)
                        write_option()
                        continue
        output.append(line)
    if action == 'add-section':
        output += ['', '[%s]' % section]
        write_option()
        print 'Created option %s = "%s" (NEW section "%s")' % \
            (key, value, section)

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
