# encoding: utf-8

import pytest


from ckan.lib.munge import (
    munge_filename_legacy,
    munge_filename,
    munge_name,
    munge_title_to_name,
    munge_tag,
)


@pytest.mark.parametrize(
    "original,expected",
    [
        ("unchanged", "unchanged"),
        ("bad spaces", "bad-spaces"),
        ("s", "s__"),  # too short
        ("random:other%character&", "randomothercharacter"),
        (u"u with umlaut \xfc", "u-with-umlaut-u"),
        (
            "2014-11-10 12:24:05.340603my_image.jpeg",
            "2014-11-10-122405.340603myimage.jpeg",
        ),
        ("file.csv", "file.csv"),
        ("f" * 100 + ".csv", "f" * 100),
        ("path/to/file.csv", "pathtofile.csv"),
        (".longextension", ".longextension"),
        ("a.longextension", "a.longextension"),
        (".1", ".1_"),
    ],
)
def test_munge_filename_legacy_pass(original, expected):
    """Munging filename multiple times produces same result."""
    first_munge = munge_filename_legacy(original)
    assert first_munge == expected
    second_munge = munge_filename_legacy(first_munge)
    assert second_munge == expected


@pytest.mark.parametrize(
    "original,expected",
    [
        ("unchanged", "unchanged"),
        ("bad spaces", "bad-spaces"),
        ("s", "s__"),  # too short
        ("random:other%character&", "randomothercharacter"),
        (u"u with umlaut \xfc", "u-with-umlaut-u"),
        (
            "2014-11-10 12:24:05.340603my_image.jpeg",
            "2014-11-10-122405.340603my_image.jpeg",
        ),
        ("file.csv", "file.csv"),
        ("underscores_are_awesome", "underscores_are_awesome"),
        ("f" * 100 + ".csv", "f" * 96 + ".csv"),
        ("path/to/file.csv", "file.csv"),
        (".longextension", ".longextension"),
        ("a.longextension", "a.longextension"),
        ("a.now_that_extension_is_too_long", "a.now_that_extension_i"),
        (".1", ".1_"),
    ],
)
def test_munge_filename_pass(original, expected):
    """Munging filename multiple times produces same result."""
    first_munge = munge_filename(original)
    assert first_munge == expected
    assert isinstance(first_munge, str)
    second_munge = munge_filename(first_munge)
    assert second_munge == expected
    assert isinstance(second_munge, str)


@pytest.mark.parametrize(
    "original,expected",
    [
        ("unchanged", "unchanged"),
        ("bad spaces", "bad-spaces"),
        ("s", "s_"),  # too short
        ("random:other%character&", "random-othercharacter"),
        (u"u with umlaut \xfc", "u-with-umlaut-u"),
        ("2014-11-10 12:24:05.my_image", "2014-11-10-12-24-05-my_image"),
    ],
)
def test_munge_name_pass(original, expected):
    """Munging name multiple times produces same result."""
    first_munge = munge_name(original)
    assert first_munge == expected
    second_munge = munge_name(first_munge)
    assert second_munge == expected


@pytest.mark.parametrize(
    "original,expected",
    [
        ("unchanged", "unchanged"),
        ("some spaces  here    &here", "some-spaces-here-here"),
        ("s", "s_"),  # too short
        ("random:other%character&", "random-othercharacter"),
        (u"u with umlaut \xfc", "u-with-umlaut-u"),
        ("reallylong" * 12, "reallylong" * 9 + "reall"),
        ("reallylong" * 12 + " - 2012", "reallylong" * 9 + "-2012"),
        (
            "10cm - 50cm Near InfraRed (NI) Digital Aerial Photography (AfA142)",
            "10cm-50cm-near-infrared-ni-digital-aerial-photography-afa142",
        ),
    ],
)
def test_munge_title_to_name(original, expected):
    """Munge a list of names gives expected results."""
    munge = munge_title_to_name(original)
    assert munge == expected


@pytest.mark.parametrize(
    "original,expected",
    [
        ("unchanged", "unchanged"),
        ("s", "s_"),  # too short
        ("some spaces  here", "some-spaces--here"),
        ("random:other%characters&_.here", "randomothercharactershere"),
        ("river-water-dashes", "river-water-dashes"),
    ],
)
def test_munge_tag_multiple_pass(original, expected):
    """Munge a list of tags muliple times gives expected results."""

    first_munge = munge_tag(original)
    assert first_munge == expected
    second_munge = munge_tag(first_munge)
    assert second_munge == expected
