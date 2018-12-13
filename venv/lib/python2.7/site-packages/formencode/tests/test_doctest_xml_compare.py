import sys

import formencode.doctest_xml_compare as dxml


XML = dxml.ET.XML
tostring = dxml.ET.tostring


def test_xml_compare():
    t1 = XML('<test />')
    t2 = XML('<test/>')
    assert dxml.xml_compare(t1, t2, sys.stdout.write)
    assert dxml.xml_compare(XML('''<hey>
    <you>!!</you>  </hey>'''), XML('<hey><you>!!</you></hey>'),
                            sys.stdout.write)
