# -*- coding: Latin-1 -*-
"""
PySourceColor: color Python source code
"""

"""
 PySourceColor.py

----------------------------------------------------------------------------

 A python source to colorized html/css/xhtml converter.
 Hacked by M.E.Farmer Jr. 2004, 2005
 Python license

----------------------------------------------------------------------------

 - HTML markup does not create w3c valid html, but it works on every
   browser i've tried so far.(I.E.,Mozilla/Firefox,Opera,Konqueror,wxHTML).
 - CSS markup is w3c validated html 4.01 strict,
   but will not render correctly on all browsers.
 - XHTML markup is w3c validated xhtml 1.0 strict,
   like html 4.01, will not render correctly on all browsers.

----------------------------------------------------------------------------

Features:

 -Three types of markup:
    html (default) 
    css/html 4.01 strict
    xhtml 1.0 strict

 -Can tokenize and colorize:
    12 types of strings
    2 comment types
    numbers
    operators
    brackets
    math operators
    class / name
    def / name
    decorator / name
    keywords
    arguments class/def/decorator
    linenumbers
    names
    text

 -Eight colorschemes built-in:
    null
    mono
    lite (default)
    dark 
    dark2
    idle
    viewcvs
    pythonwin

 -Header and footer
    set to '' for builtin header / footer.
    give path to a file containing the html
        you want added as header or footer.

 -Arbitrary text and html
    html markup converts all to raw (TEXT token)
    #@# for raw -> send raw text.
    #$# for span -> inline html and text.
    #%# for div -> block level html and text.

 -Linenumbers
    Supports all styles. New token is called LINENUMBER.
    Defaults to NAME if not defined.

 Style options
 
 -ALL markups support these text styles:
         b = bold
         i = italic
         u = underline
 -CSS and XHTML has limited support  for borders:
     HTML markup functions will ignore these.
     Optional: Border color in RGB hex
     Defaults to the text forecolor.
         #rrggbb = border color
     Border size:
         l = thick
         m = medium
         t = thin
     Border type:
         - = dashed
         . = dotted
         s = solid
         d = double
         g = groove
         r = ridge
         n = inset
         o = outset
     You can specify multiple sides,
     they will all use the same style.
     Optional: Default is full border.
         v = bottom
         < = left
         > = right
         ^ = top
     NOTE: Specify the styles you want.
           The markups will ignore unsupported styles
           Also note not all browsers can show these options

 -All tokens default to NAME if not defined
     so the only absolutely critical ones to define are:
     NAME, ERRORTOKEN, PAGEBACKGROUND

----------------------------------------------------------------------------

Example usage::

 # import
 import PySourceColor as psc
 psc.convert('c:/Python22/PySourceColor.py', colors=psc.idle, show=1)

 # from module import *
 from PySourceColor import *
 convert('c:/Python22/Lib', colors=lite, markup="css",
          header='#$#<b>This is a simpe heading</b><hr/>')

 # How to use a custom colorscheme, and most of the 'features'
 from PySourceColor import *
 new = {
   ERRORTOKEN:             ('bui','#FF8080',''),
   DECORATOR_NAME:         ('s','#AACBBC',''),
   DECORATOR:              ('n','#333333',''),
   NAME:                   ('t.<v','#1133AA','#DDFF22'),
   NUMBER:                 ('','#236676','#FF5555'),
   OPERATOR:               ('b','#454567','#BBBB11'),
   MATH_OPERATOR:          ('','#935623','#423afb'),
   BRACKETS:               ('b','#ac34bf','#6457a5'),
   COMMENT:                ('t-#0022FF','#545366','#AABBFF'),
   DOUBLECOMMENT:          ('<l#553455','#553455','#FF00FF'),
   CLASS_NAME:             ('m^v-','#000000','#FFFFFF'),
   DEF_NAME:               ('l=<v','#897845','#000022'),
   KEYWORD:                ('.b','#345345','#FFFF22'),
   SINGLEQUOTE:            ('mn','#223344','#AADDCC'),
   SINGLEQUOTE_R:          ('','#344522',''),
   SINGLEQUOTE_U:          ('','#234234',''),
   DOUBLEQUOTE:            ('m#0022FF','#334421',''),
   DOUBLEQUOTE_R:          ('','#345345',''),
   DOUBLEQUOTE_U:          ('','#678673',''),
   TRIPLESINGLEQUOTE:      ('tv','#FFFFFF','#000000'),
   TRIPLESINGLEQUOTE_R:    ('tbu','#443256','#DDFFDA'),
   TRIPLESINGLEQUOTE_U:    ('','#423454','#DDFFDA'),
   TRIPLEDOUBLEQUOTE:      ('li#236fd3b<>','#000000','#FFFFFF'),
   TRIPLEDOUBLEQUOTE_R:    ('tub','#000000','#FFFFFF'),
   TRIPLEDOUBLEQUOTE_U:    ('-', '#CCAABB','#FFFAFF'),
   LINENUMBER:             ('ib-','#ff66aa','#7733FF'),]
   TEXT:                   ('','#546634',''), 
   PAGEBACKGROUND:         '#FFFAAA',
     }
 if __name__ == '__main__':
     import sys
     convert(sys.argv[1], './xhtml.html', colors=new, markup='xhtml', show=1,
             linenumbers=1)
     convert(sys.argv[1], './html.html', colors=new, markup='html', show=1,
             linenumbers=1)

"""

__all__ = ['ERRORTOKEN','DECORATOR_NAME', 'DECORATOR', 'ARGS', 'EXTRASPACE',
       'NAME', 'NUMBER', 'OPERATOR', 'COMMENT', 'MATH_OPERATOR',
       'DOUBLECOMMENT', 'CLASS_NAME', 'DEF_NAME', 'KEYWORD', 'BRACKETS',
       'SINGLEQUOTE','SINGLEQUOTE_R','SINGLEQUOTE_U','DOUBLEQUOTE',
       'DOUBLEQUOTE_R', 'DOUBLEQUOTE_U', 'TRIPLESINGLEQUOTE', 'TEXT', 
       'TRIPLESINGLEQUOTE_R', 'TRIPLESINGLEQUOTE_U', 'TRIPLEDOUBLEQUOTE',
       'TRIPLEDOUBLEQUOTE_R', 'TRIPLEDOUBLEQUOTE_U', 'PAGEBACKGROUND',
       'LINENUMBER', 'CODESTART', 'CODEEND', 'PY', 'TOKEN_NAMES', 'CSSHOOK',
       'null', 'mono', 'lite', 'dark','dark2', 'pythonwin','idle', 
       'viewcvs', 'Usage', 'cli', 'str2stdout', 'path2stdout', 'Parser',
       'str2file', 'str2html', 'str2css', 'str2markup', 'path2file',
       'path2html', 'convert', 'walkdir', 'defaultColors', 'showpage',
       'pageconvert','tagreplace', 'MARKUPDICT']
__title__ = 'PySourceColor'
__version__ = "2.1a"
__date__ = '25 April 2005'
__author__ = "M.E.Farmer Jr."
__credits__ = '''This was originally based on a python recipe
submitted by Jürgen Hermann to ASPN. Now based on the voices in my head.
M.E.Farmer 2004, 2005
Python license
'''
import os
import sys
import time
import glob
import getopt
import keyword
import token
import tokenize
import traceback
try :
    import cStringIO as StringIO
except:
    import StringIO
# Do not edit
NAME = token.NAME
NUMBER = token.NUMBER
COMMENT = tokenize.COMMENT
OPERATOR = token.OP
ERRORTOKEN = token.ERRORTOKEN
ARGS = token.NT_OFFSET + 1
DOUBLECOMMENT = token.NT_OFFSET + 2
CLASS_NAME = token.NT_OFFSET + 3
DEF_NAME = token.NT_OFFSET + 4
KEYWORD = token.NT_OFFSET + 5
SINGLEQUOTE = token.NT_OFFSET + 6
SINGLEQUOTE_R = token.NT_OFFSET + 7
SINGLEQUOTE_U = token.NT_OFFSET + 8
DOUBLEQUOTE = token.NT_OFFSET + 9
DOUBLEQUOTE_R = token.NT_OFFSET + 10
DOUBLEQUOTE_U = token.NT_OFFSET + 11
TRIPLESINGLEQUOTE = token.NT_OFFSET + 12
TRIPLESINGLEQUOTE_R = token.NT_OFFSET + 13
TRIPLESINGLEQUOTE_U = token.NT_OFFSET + 14
TRIPLEDOUBLEQUOTE = token.NT_OFFSET + 15
TRIPLEDOUBLEQUOTE_R = token.NT_OFFSET + 16
TRIPLEDOUBLEQUOTE_U = token.NT_OFFSET + 17
PAGEBACKGROUND = token.NT_OFFSET + 18
DECORATOR = token.NT_OFFSET + 19
DECORATOR_NAME = token.NT_OFFSET + 20
BRACKETS = token.NT_OFFSET + 21
MATH_OPERATOR = token.NT_OFFSET + 22
LINENUMBER = token.NT_OFFSET + 23
TEXT = token.NT_OFFSET + 24
PY = token.NT_OFFSET + 25
CODESTART = token.NT_OFFSET + 26
CODEEND = token.NT_OFFSET + 27
CSSHOOK = token.NT_OFFSET + 28
EXTRASPACE = token.NT_OFFSET + 29

# markup classname lookup
MARKUPDICT = {
        ERRORTOKEN:             'py_err',
        DECORATOR_NAME:         'py_decn',
        DECORATOR:              'py_dec',
        ARGS:                   'py_args',
        NAME:                   'py_name',
        NUMBER:                 'py_num',
        OPERATOR:               'py_op',
        COMMENT:                'py_com',
        DOUBLECOMMENT:          'py_dcom',
        CLASS_NAME:             'py_clsn',
        DEF_NAME:               'py_defn',
        KEYWORD:                'py_key',
        SINGLEQUOTE:            'py_sq',
        SINGLEQUOTE_R:          'py_sqr',
        SINGLEQUOTE_U:          'py_squ',
        DOUBLEQUOTE:            'py_dq',
        DOUBLEQUOTE_R:          'py_dqr',
        DOUBLEQUOTE_U:          'py_dqu',
        TRIPLESINGLEQUOTE:      'py_tsq',
        TRIPLESINGLEQUOTE_R:    'py_tsqr',
        TRIPLESINGLEQUOTE_U:    'py_tsqu',
        TRIPLEDOUBLEQUOTE:      'py_tdq',
        TRIPLEDOUBLEQUOTE_R:    'py_tdqr',
        TRIPLEDOUBLEQUOTE_U:    'py_tdqu',
        BRACKETS:               'py_bra',
        MATH_OPERATOR:          'py_mop',
        LINENUMBER:             'py_lnum',
        TEXT:                   'py_text',
        }
# might help users that want to create custom schemes
TOKEN_NAMES= {
       ERRORTOKEN:'ERRORTOKEN',
       DECORATOR_NAME:'DECORATOR_NAME',
       DECORATOR:'DECORATOR',
       ARGS:'ARGS',
       NAME:'NAME',
       NUMBER:'NUMBER',
       OPERATOR:'OPERATOR',
       COMMENT:'COMMENT',
       DOUBLECOMMENT:'DOUBLECOMMENT',
       CLASS_NAME:'CLASS_NAME',
       DEF_NAME:'DEF_NAME',
       KEYWORD:'KEYWORD',
       SINGLEQUOTE:'SINGLEQUOTE',
       SINGLEQUOTE_R:'SINGLEQUOTE_R',
       SINGLEQUOTE_U:'SINGLEQUOTE_U',
       DOUBLEQUOTE:'DOUBLEQUOTE',
       DOUBLEQUOTE_R:'DOUBLEQUOTE_R',
       DOUBLEQUOTE_U:'DOUBLEQUOTE_U',
       TRIPLESINGLEQUOTE:'TRIPLESINGLEQUOTE',
       TRIPLESINGLEQUOTE_R:'TRIPLESINGLEQUOTE_R',
       TRIPLESINGLEQUOTE_U:'TRIPLESINGLEQUOTE_U',
       TRIPLEDOUBLEQUOTE:'TRIPLEDOUBLEQUOTE',
       TRIPLEDOUBLEQUOTE_R:'TRIPLEDOUBLEQUOTE_R',
       TRIPLEDOUBLEQUOTE_U:'TRIPLEDOUBLEQUOTE_U',
       BRACKETS:'BRACKETS',
       MATH_OPERATOR:'MATH_OPERATOR',
       LINENUMBER:'LINENUMBER',
       TEXT:'TEXT',
       PAGEBACKGROUND:'PAGEBACKGROUND',
       }

######################################################################
# Edit colors and styles to taste
# Create your own scheme, just copy one below , rename and edit.
# Custom styles must at least define NAME, ERRORTOKEN, PAGEBACKGROUND,
# all missing elements will default to NAME.
# See module docstring for details on style attributes.
######################################################################
# Copy null and use it as a starter colorscheme.
null = {# tokentype: ('tags border_color', 'textforecolor', 'textbackcolor')
        ERRORTOKEN:             ('','#000000',''),# Error token
        DECORATOR_NAME:         ('','#000000',''),# Decorator name
        DECORATOR:              ('','#000000',''),# @ symbol
        ARGS:                   ('','#000000',''),# class,def,deco arguments
        NAME:                   ('','#000000',''),# All other python text
        NUMBER:                 ('','#000000',''),# 0->10
        OPERATOR:               ('','#000000',''),# ':','<=',';',',','.','==', etc
        MATH_OPERATOR:          ('','#000000',''),# '+','-','=','','**',etc
        BRACKETS:               ('','#000000',''),# '[',']','(',')','{','}'
        COMMENT:                ('','#000000',''),# Single comment
        DOUBLECOMMENT:          ('','#000000',''),## Double comment
        CLASS_NAME:             ('','#000000',''),# Class name
        DEF_NAME:               ('','#000000',''),# Def name
        KEYWORD:                ('','#000000',''),# Python keywords
        SINGLEQUOTE:            ('','#000000',''),# 'SINGLEQUOTE'
        SINGLEQUOTE_R:          ('','#000000',''),# r'SINGLEQUOTE'
        SINGLEQUOTE_U:          ('','#000000',''),# u'SINGLEQUOTE'
        DOUBLEQUOTE:            ('','#000000',''),# "DOUBLEQUOTE"
        DOUBLEQUOTE_R:          ('','#000000',''),# r"DOUBLEQUOTE"
        DOUBLEQUOTE_U:          ('','#000000',''),# u"DOUBLEQUOTE"
        TRIPLESINGLEQUOTE:      ('','#000000',''),# '''TRIPLESINGLEQUOTE'''
        TRIPLESINGLEQUOTE_R:    ('','#000000',''),# r'''TRIPLESINGLEQUOTE'''
        TRIPLESINGLEQUOTE_U:    ('','#000000',''),# u'''TRIPLESINGLEQUOTE'''
        TRIPLEDOUBLEQUOTE:      ('','#000000',''),# """TRIPLEDOUBLEQUOTE"""
        TRIPLEDOUBLEQUOTE_R:    ('','#000000',''),# r"""TRIPLEDOUBLEQUOTE"""
        TRIPLEDOUBLEQUOTE_U:    ('','#000000',''),# u"""TRIPLEDOUBLEQUOTE"""
        TEXT:                   ('','#000000',''),# non python text 
        LINENUMBER:             ('>ti#555555','#000000',''),# Linenumbers
        PAGEBACKGROUND:         '#FFFFFF'# set the page background
        }

mono = {
        ERRORTOKEN:             ('s#FF0000','#FF8080',''),
        DECORATOR_NAME:         ('bu','#000000',''),
        DECORATOR:              ('b','#000000',''),
        ARGS:                   ('b','#555555',''),
        NAME:                   ('','#000000',''),
        NUMBER:                 ('b','#000000',''),
        OPERATOR:               ('b','#000000',''),
        MATH_OPERATOR:          ('b','#000000',''),
        BRACKETS:               ('b','#000000',''),
        COMMENT:                ('i','#999999',''),
        DOUBLECOMMENT:          ('b','#999999',''),
        CLASS_NAME:             ('bu','#000000',''),
        DEF_NAME:               ('b','#000000',''),
        KEYWORD:                ('b','#000000',''),
        SINGLEQUOTE:            ('','#000000',''),
        SINGLEQUOTE_R:          ('','#000000',''),
        SINGLEQUOTE_U:          ('','#000000',''),
        DOUBLEQUOTE:            ('','#000000',''),
        DOUBLEQUOTE_R:          ('','#000000',''),
        DOUBLEQUOTE_U:          ('','#000000',''),
        TRIPLESINGLEQUOTE:      ('','#000000',''),
        TRIPLESINGLEQUOTE_R:    ('','#000000',''),
        TRIPLESINGLEQUOTE_U:    ('','#000000',''),
        TRIPLEDOUBLEQUOTE:      ('i','#000000',''),
        TRIPLEDOUBLEQUOTE_R:    ('i','#000000',''),
        TRIPLEDOUBLEQUOTE_U:    ('i','#000000',''),
        TEXT:                   ('','#000000',''),
        LINENUMBER:             ('>ti#555555','#000000',''),
        PAGEBACKGROUND:         '#FFFFFF'
        }

dark = {
        ERRORTOKEN:             ('s#FF0000','#FF8080',''),
        DECORATOR_NAME:         ('b','#FFBBAA',''),
        DECORATOR:              ('b','#CC5511',''),
        ARGS:                   ('b','#DDDDFF',''),
        NAME:                   ('','#DDDDDD',''),
        NUMBER:                 ('','#FF0000',''),
        OPERATOR:               ('b','#FAF785',''),
        MATH_OPERATOR:          ('b','#FAF785',''),
        BRACKETS:               ('b','#FAF785',''),
        COMMENT:                ('','#45FCA0',''),
        DOUBLECOMMENT:          ('i','#A7C7A9',''),
        CLASS_NAME:             ('b','#B666FD',''),
        DEF_NAME:               ('b','#EBAE5C',''),
        KEYWORD:                ('b','#8680FF',''),
        SINGLEQUOTE:            ('','#F8BAFE',''),
        SINGLEQUOTE_R:          ('','#F8BAFE',''),
        SINGLEQUOTE_U:          ('','#F8BAFE',''),
        DOUBLEQUOTE:            ('','#FF80C0',''),
        DOUBLEQUOTE_R:          ('','#FF80C0',''),
        DOUBLEQUOTE_U:          ('','#FF80C0',''),
        TRIPLESINGLEQUOTE:      ('','#FF9595',''),
        TRIPLESINGLEQUOTE_R:    ('','#FF9595',''),
        TRIPLESINGLEQUOTE_U:    ('','#FF9595',''),
        TRIPLEDOUBLEQUOTE:      ('','#B3FFFF',''),
        TRIPLEDOUBLEQUOTE_R:    ('','#B3FFFF',''),
        TRIPLEDOUBLEQUOTE_U:    ('','#B3FFFF',''),
        TEXT:                   ('','#FFFFFF',''),
        LINENUMBER:             ('>mi#555555','#bbccbb','#333333'),
        PAGEBACKGROUND:         '#000000'
        }

dark2 = {
        ERRORTOKEN:             ('','#FF0000',''),
        DECORATOR_NAME:         ('b','#FFBBAA',''),
        DECORATOR:              ('b','#CC5511',''),
        ARGS:                   ('b','#DDDDDD',''),
        NAME:                   ('','#C0C0C0',''),
        NUMBER:                 ('b','#00FF00',''),
        OPERATOR:               ('b','#FF090F',''),
        MATH_OPERATOR:          ('b','#EE7020',''),
        BRACKETS:               ('b','#FFB90F',''),
        COMMENT:                ('i','#D0D000','#522000'),#'#88AA88','#11111F'),
        DOUBLECOMMENT:          ('i','#D0D000','#522000'),#'#77BB77','#11111F'),
        CLASS_NAME:             ('b','#DD4080',''),
        DEF_NAME:               ('b','#FF8040',''),
        KEYWORD:                ('b','#4726d1',''),
        SINGLEQUOTE:            ('','#8080C0',''),
        SINGLEQUOTE_R:          ('','#8080C0',''),
        SINGLEQUOTE_U:          ('','#8080C0',''),
        DOUBLEQUOTE:            ('','#ADB9F1',''),
        DOUBLEQUOTE_R:          ('','#ADB9F1',''),
        DOUBLEQUOTE_U:          ('','#ADB9F1',''),
        TRIPLESINGLEQUOTE:      ('','#00C1C1',''),#A050C0
        TRIPLESINGLEQUOTE_R:    ('','#00C1C1',''),#A050C0
        TRIPLESINGLEQUOTE_U:    ('','#00C1C1',''),#A050C0
        TRIPLEDOUBLEQUOTE:      ('','#33E3E3',''),#B090E0
        TRIPLEDOUBLEQUOTE_R:    ('','#33E3E3',''),#B090E0
        TRIPLEDOUBLEQUOTE_U:    ('','#33E3E3',''),#B090E0
        TEXT:                   ('','#C0C0C0',''),
        LINENUMBER:             ('>mi#555555','#bbccbb','#333333'),
        PAGEBACKGROUND:         '#000000'
        }

lite = {
        ERRORTOKEN:             ('s#FF0000','#FF8080',''),
        DECORATOR_NAME:         ('b','#BB4422',''),
        DECORATOR:              ('b','#3333AF',''),
        ARGS:                   ('b','#000000',''),
        NAME:                   ('','#333333',''),
        NUMBER:                 ('b','#DD2200',''),
        OPERATOR:               ('b','#000000',''),
        MATH_OPERATOR:          ('b','#000000',''),
        BRACKETS:               ('b','#000000',''),
        COMMENT:                ('','#007F00',''),
        DOUBLECOMMENT:          ('','#608060',''),
        CLASS_NAME:             ('b','#0000DF',''),
        DEF_NAME:               ('b','#9C7A00',''),#f09030
        KEYWORD:                ('b','#0000AF',''),
        SINGLEQUOTE:            ('','#600080',''),
        SINGLEQUOTE_R:          ('','#600080',''),
        SINGLEQUOTE_U:          ('','#600080',''),
        DOUBLEQUOTE:            ('','#A0008A',''),
        DOUBLEQUOTE_R:          ('','#A0008A',''),
        DOUBLEQUOTE_U:          ('','#A0008A',''),
        TRIPLESINGLEQUOTE:      ('','#337799',''),
        TRIPLESINGLEQUOTE_R:    ('','#337799',''),
        TRIPLESINGLEQUOTE_U:    ('','#337799',''),
        TRIPLEDOUBLEQUOTE:      ('','#1166AA',''),
        TRIPLEDOUBLEQUOTE_R:    ('','#1166AA',''),
        TRIPLEDOUBLEQUOTE_U:    ('','#1166AA',''),
        TEXT:                   ('','#000000',''),
        LINENUMBER:             ('>ti#555555','#000000',''),
        PAGEBACKGROUND:         '#FFFFFF'
        }

idle = {
        ERRORTOKEN:             ('s#FF0000','#FF8080',''),
        DECORATOR_NAME:         ('','#900090',''),
        DECORATOR:              ('','#FF7700',''),
        NAME:                   ('','#000000',''),
        NUMBER:                 ('','#000000',''),
        OPERATOR:               ('','#000000',''),
        MATH_OPERATOR:          ('','#000000',''),
        BRACKETS:               ('','#000000',''),
        COMMENT:                ('','#DD0000',''),
        DOUBLECOMMENT:          ('','#DD0000',''),
        CLASS_NAME:             ('','#0000FF',''),
        DEF_NAME:               ('','#0000FF',''),
        KEYWORD:                ('','#FF7700',''),
        SINGLEQUOTE:            ('','#00AA00',''),
        SINGLEQUOTE_R:          ('','#00AA00',''),
        SINGLEQUOTE_U:          ('','#00AA00',''),
        DOUBLEQUOTE:            ('','#00AA00',''),
        DOUBLEQUOTE_R:          ('','#00AA00',''),
        DOUBLEQUOTE_U:          ('','#00AA00',''),
        TRIPLESINGLEQUOTE:      ('','#00AA00',''),
        TRIPLESINGLEQUOTE_R:    ('','#00AA00',''),
        TRIPLESINGLEQUOTE_U:    ('','#00AA00',''),
        TRIPLEDOUBLEQUOTE:      ('','#00AA00',''),
        TRIPLEDOUBLEQUOTE_R:    ('','#00AA00',''),
        TRIPLEDOUBLEQUOTE_U:    ('','#00AA00',''),
        TEXT:                   ('','#000000',''),
        LINENUMBER:             ('>ti#555555','#000000',''),
        PAGEBACKGROUND:         '#FFFFFF'
        }

pythonwin = {
        ERRORTOKEN:             ('s#FF0000','#FF8080',''),
        DECORATOR_NAME:         ('b','#DD0080',''),
        DECORATOR:              ('b','#000080',''),
        ARGS:                   ('','#000000',''),
        NAME:                   ('','#303030',''),
        NUMBER:                 ('','#008080',''),
        OPERATOR:               ('','#000000',''),
        MATH_OPERATOR:          ('','#000000',''),
        BRACKETS:               ('','#000000',''),
        COMMENT:                ('','#007F00',''),
        DOUBLECOMMENT:          ('','#7F7F7F',''),
        CLASS_NAME:             ('b','#0000FF',''),
        DEF_NAME:               ('b','#007F7F',''),
        KEYWORD:                ('b','#000080',''),
        SINGLEQUOTE:            ('','#808000',''),
        SINGLEQUOTE_R:          ('','#808000',''),
        SINGLEQUOTE_U:          ('','#808000',''),
        DOUBLEQUOTE:            ('','#808000',''),
        DOUBLEQUOTE_R:          ('','#808000',''),
        DOUBLEQUOTE_U:          ('','#808000',''),
        TRIPLESINGLEQUOTE:      ('','#808000',''),
        TRIPLESINGLEQUOTE_R:    ('','#808000',''),
        TRIPLESINGLEQUOTE_U:    ('','#808000',''),
        TRIPLEDOUBLEQUOTE:      ('','#808000',''),
        TRIPLEDOUBLEQUOTE_R:    ('','#808000',''),
        TRIPLEDOUBLEQUOTE_U:    ('','#808000',''),
        TEXT:                   ('','#303030',''),
        LINENUMBER:             ('>ti#555555','#000000',''),
        PAGEBACKGROUND:         '#FFFFFF'
        }

viewcvs = {
        ERRORTOKEN:             ('s#FF0000','#FF8080',''),
        DECORATOR_NAME:         ('','#000000',''),
        DECORATOR:              ('','#000000',''),
        ARGS:                   ('','#000000',''),
        NAME:                   ('','#000000',''),
        NUMBER:                 ('','#000000',''),
        OPERATOR:               ('','#000000',''),
        MATH_OPERATOR:          ('','#000000',''),
        BRACKETS:               ('','#000000',''),
        COMMENT:                ('i','#b22222',''),
        DOUBLECOMMENT:          ('i','#b22222',''),
        CLASS_NAME:             ('','#000000',''),
        DEF_NAME:               ('b','#0000ff',''),
        KEYWORD:                ('b','#a020f0',''),
        SINGLEQUOTE:            ('b','#bc8f8f',''),
        SINGLEQUOTE_R:          ('b','#bc8f8f',''),
        SINGLEQUOTE_U:          ('b','#bc8f8f',''),
        DOUBLEQUOTE:            ('b','#bc8f8f',''),
        DOUBLEQUOTE_R:          ('b','#bc8f8f',''),
        DOUBLEQUOTE_U:          ('b','#bc8f8f',''),
        TRIPLESINGLEQUOTE:      ('b','#bc8f8f',''),
        TRIPLESINGLEQUOTE_R:    ('b','#bc8f8f',''),
        TRIPLESINGLEQUOTE_U:    ('b','#bc8f8f',''),
        TRIPLEDOUBLEQUOTE:      ('b','#bc8f8f',''),
        TRIPLEDOUBLEQUOTE_R:    ('b','#bc8f8f',''),
        TRIPLEDOUBLEQUOTE_U:    ('b','#bc8f8f',''),
        TEXT:                   ('','#000000',''),
        LINENUMBER:             ('>ti#555555','#000000',''),
        PAGEBACKGROUND:         '#FFFFFF'
        }

defaultColors = lite

def Usage():
    doc = """
 -----------------------------------------------------------------------------
  PySourceColor.py ver: %s
 -----------------------------------------------------------------------------
  Module summary:
     This module is designed to colorize python source code.
         Input--->python source
         Output-->colorized (html, html4.01/css, xhtml1.0)
     Standalone:
         This module will work from the command line with options.
         This module will work with redirected stdio.
     Imported:
         This module can be imported and used directly in your code.
 -----------------------------------------------------------------------------
  Command line options:
     -h, --help
         Optional-> Display this help message.
     -t, --test
         Optional-> Will ignore all others flags but  --profile
             test all schemes and markup combinations
     -p, --profile
         Optional-> Works only with --test or -t
             runs profile.py and makes the test work in quiet mode.
     -i, --in, --input
         Optional-> If you give input on stdin.
         Use any of these for the current dir (.,cwd)
         Input can be file or dir.
         Input from stdin use one of the following (-,stdin)
         If stdin is used as input stdout is output unless specified.
     -o, --out, --output
         Optional-> output dir for the colorized source.
             default: output dir is the input dir.
         To output html to stdout use one of the following (-,stdout)
         Stdout can be used without stdin if you give a file as input.
     -c, --color
         Optional-> null, mono, dark, dark2, lite, idle, pythonwin, viewcvs
             default: dark 
     -s, --show
         Optional-> Show page after creation.
             default: no show
     -m, --markup
         Optional-> html, css, xhtml
             css, xhtml also support external stylesheets (-e,--external)
             default: HTML
     -e, --external
         Optional-> use with css, xhtml
             Writes an style sheet instead of embedding it in the page
             saves it as pystyle.css in the same directory.
             html markup will silently ignore this flag.
     -H, --header
         Opional-> add a page header to the top of the output
         -H
             Builtin header (name,date,hrule)
         --header
             You must specify a filename.
             The header file must be valid html
             and must handle its own font colors.
             ex. --header c:/tmp/header.txt
     -F, --footer
         Opional-> add a page footer to the bottom of the output
         -F 
             Builtin footer (hrule,name,date)
         --footer
             You must specify a filename.
             The footer file must be valid html
             and must handle its own font colors.
             ex. --footer c:/tmp/footer.txt  
     -l, --linenumbers
         Optional-> default is no linenumbers
             Adds line numbers to the start of each line in the code.
    --convertpage
         Given a webpage that has code embedded in tags it will
             convert embedded code to colorized html. 
             (see pageconvert for details)
 -----------------------------------------------------------------------------
  Option usage:
   # Test and show pages
      python PySourceColor.py -t -s
   # Test and only show profile results
      python PySourceColor.py -t -p
   # Colorize all .py,.pyw files in cwdir you can also use: (.,cwd)
      python PySourceColor.py -i .
   # Using long options w/ =
      python PySourceColor.py --in=c:/myDir/my.py --color=lite --show
   # Using short options w/out =
      python PySourceColor.py -i c:/myDir/  -c idle -m css -e
   # Using any mix
      python PySourceColor.py --in . -o=c:/myDir --show
   # Place a custom header on your files
      python PySourceColor.py -i . -o c:/tmp -m xhtml --header c:/header.txt
 -----------------------------------------------------------------------------
  Stdio usage:
   # Stdio using no options
      python PySourceColor.py < c:/MyFile.py > c:/tmp/MyFile.html
   # Using stdin alone automatically uses stdout for output: (stdin,-)
      python PySourceColor.py -i- < c:/MyFile.py > c:/tmp/myfile.html
   # Stdout can also be written to directly from a file instead of stdin
      python PySourceColor.py -i c:/MyFile.py -m css -o- > c:/tmp/myfile.html
   # Stdin can be used as input , but output can still be specified
      python PySourceColor.py -i- -o c:/pydoc.py.html -s < c:/Python22/my.py
 _____________________________________________________________________________
 """
    print doc % (__version__)
    sys.exit(1)

###################################################### Command line interface

def cli():
    """Handle command line args and redirections"""
    try:
        # try to get command line args
        opts, args = getopt.getopt(sys.argv[1:],
              "hseqtplHFi:o:c:m:h:f:",["help", "show", "quiet", 
              "test", "external", "linenumbers", "convertpage", "profile", 
              "input=", "output=", "color=", "markup=","header=", "footer="])
    except getopt.GetoptError:
        # on error print help information and exit:
        Usage()
    # init some names
    input = None
    output = None
    colorscheme = None
    markup = 'html'
    header = None
    footer = None
    linenumbers = 0
    show = 0
    quiet = 0
    test = 0
    profile = 0
    convertpage = 0
    form = None
    # if we have args then process them
    for o, a in opts:
        if o in ["-h", "--help"]:
            Usage()
            sys.exit()
        if o in ["-o", "--output", "--out"]:
            output = a
        if o in ["-i", "--input", "--in"]:
            input = a
            if input in [".", "cwd"]:
                input = os.getcwd()
        if o in ["-s", "--show"]:
            show = 1
        if o in ["-q", "--quiet"]:
            quiet = 1
        if o in ["-t", "--test"]:
            test = 1
        if o in ["--convertpage"]:
            convertpage = 1
        if o in ["-p", "--profile"]:
            profile = 1
        if o in ["-e", "--external"]:
            form = 'external'
        if o in ["-m", "--markup"]:
            markup = str(a)
        if o in ["-l", "--linenumbers"]:
            linenumbers = 1
        if o in ["--header"]:
            header = str(a)
        elif o == "-H":
            header = ''
        if o in ["--footer"]:
            footer = str(a)
        elif o == "-F":
            footer = ''
        if o in ["-c", "--color"]:
            try:
                colorscheme = globals().get(a.lower())
            except:
                traceback.print_exc()
                Usage()
    if test:
        if profile:
            import profile
            profile.run('_test(show=%s, quiet=%s)'%(show,quiet))
        else:
            # Parse this script in every possible colorscheme and markup
            _test(show,quiet)
    elif input in [None, "-", "stdin"] or output in ["-", "stdout"]:
        # determine if we are going to use stdio
        if input not in [None, "-", "stdin"]:
            if os.path.isfile(input) :
                path2stdout(input, colors=colorscheme, markup=markup,
                            linenumbers=linenumbers, header=header, 
                            footer=footer, form=form)
            else:
                raise PathError, 'File does not exists!'
        else:
            try:
                if sys.stdin.isatty():
                    raise InputError, 'Please check input!'
                else:
                    if output in [None,"-","stdout"]:
                        str2stdout(sys.stdin.read(), colors=colorscheme,
                                   markup=markup, header=header,
                                   footer=footer, linenumbers=linenumbers,
                                   form=form)
                    else:
                        str2file(sys.stdin.read(), outfile=output, show=show, 
                                markup=markup, header=header, footer=footer,
                                linenumbers=linenumbers, form=form)
            except:
                traceback.print_exc()
                Usage()
    else:
        if os.path.exists(input):
            if convertpage:
                # if there was at least an input given we can proceed
                pageconvert(input, out=output, colors=colorscheme, 
                            show=show, markup=markup,linenumbers=linenumbers)
            else:
                # if there was at least an input given we can proceed
                convert(source=input, outdir=output, colors=colorscheme, 
                        show=show, markup=markup, quiet=quiet, header=header,
                        footer=footer, linenumbers=linenumbers, form=form)
        else:
            raise PathError, 'File does not exists!'
            Usage()

######################################################### Simple markup tests

def _test(show=0, quiet=0):
    """Test the parser and most of the functions.

       There are 19 test total(eight colorschemes in three diffrent markups,
       and a str2file test. Most functions are tested by this.
    """
    fi = sys.argv[0]
    if not fi.endswith('.exe'):# Do not test if frozen as an archive
        # this is a collection of test, most things are covered.
        path2file(fi, '/tmp/null.html', null, show=show, quiet=quiet)
        path2file(fi, '/tmp/null_css.html', null, show=show,
                  markup='css', quiet=quiet)
        path2file(fi, '/tmp/mono.html', mono, show=show, quiet=quiet)
        path2file(fi, '/tmp/mono_css.html', mono, show=show,
                  markup='css', quiet=quiet)
        path2file(fi, '/tmp/lite.html', lite, show=show, quiet=quiet)
        path2file(fi, '/tmp/lite_css.html', lite, show=show,
                  markup='css', quiet=quiet, header='', footer='', 
                  linenumbers=1)
        path2file(fi, '/tmp/lite_xhtml.html', lite, show=show,
                  markup='xhtml', quiet=quiet)
        path2file(fi, '/tmp/dark.html', dark, show=show, quiet=quiet)
        path2file(fi, '/tmp/dark_css.html', dark, show=show,
                  markup='css', quiet=quiet, linenumbers=1)
        path2file(fi, '/tmp/dark2.html', dark2, show=show, quiet=quiet)
        path2file(fi, '/tmp/dark2_css.html', dark2, show=show,
                  markup='css', quiet=quiet)
        path2file(fi, '/tmp/dark2_xhtml.html', dark2, show=show,
                  markup='xhtml', quiet=quiet, header='', footer='', 
                  linenumbers=1, form='external')
        path2file(fi, '/tmp/idle.html', idle, show=show, quiet=quiet)
        path2file(fi, '/tmp/idle_css.html', idle, show=show,
                  markup='css', quiet=quiet)
        path2file(fi, '/tmp/viewcvs.html', viewcvs, show=show, 
                  quiet=quiet, linenumbers=1)
        path2file(fi, '/tmp/viewcvs_css.html', viewcvs, show=show,
                  markup='css', linenumbers=1, quiet=quiet)
        path2file(fi, '/tmp/pythonwin.html', pythonwin, show=show,
                  quiet=quiet)
        path2file(fi, '/tmp/pythonwin_css.html', pythonwin, show=show,
                  markup='css', quiet=quiet)
        teststr=r'''"""This is a test of decorators and other things"""
# This should be line 421...
@whatever(arg,arg2)
@A @B(arghh) @C
def LlamaSaysNi(arg='Ni!',arg2="RALPH"):
   """This docstring is deeply disturbed by all the llama references"""
   print '%s The Wonder Llama says %s'% (arg2,arg)
# So I was like duh!, and he was like ya know?!,
# and so we were both like huh...wtf!? RTFM!! LOL!!;)
@staticmethod## Double comments are KewL.
def LlamasRLumpy():
   """This docstring is too sexy to be here.
   """
   u"""
=============================
A Møøse once bit my sister...
=============================
   """
   ## Relax, this won't hurt a bit, just a simple, painless procedure,
   ## hold still while I get the anesthetizing hammer.
   m = {'three':'1','won':'2','too':'3'}
   o = r'fishy\fishy\fishy/fish\oh/where/is\my/little\..'
   python = uR""" 
 No realli! She was Karving her initials øn the møøse with the sharpened end  
 of an interspace tøøthbrush given her by Svenge - her brother-in-law -an Oslo
 dentist and star of many Norwegian møvies: "The Høt Hands of an Oslo         
 Dentist", "Fillings of Passion", "The Huge Mølars of Horst Nordfink"..."""
   RU"""142 MEXICAN WHOOPING LLAMAS"""#<-Can you fit 142 llamas in a red box?
   n = u' HERMSGERVØRDENBRØTBØRDA ' + """ YUTTE """
   t = """SAMALLNIATNUOMNAIRODAUCE"""+"DENIARTYLLAICEPS04"
   ## We apologise for the fault in the
   ## comments. Those responsible have been
   ## sacked.
   y = '14 NORTH CHILEAN GUANACOS \
(CLOSELY RELATED TO THE LLAMA)'
   rules = [0,1,2,3,4,5]
   print y'''
        htmlPath = os.path.abspath('/tmp/strtest_lines.html')
        str2file(teststr, htmlPath, colors=dark, markup='xhtml',
                 linenumbers=420, show=show)
        _printinfo("  wrote %s" % htmlPath, quiet)
        htmlPath = os.path.abspath('/tmp/strtest_nolines.html')
        str2file(teststr, htmlPath, colors=dark, markup='xhtml',
                 show=show)
        _printinfo("  wrote %s" % htmlPath, quiet)
    else:
        Usage()
    return

# emacs wants this: '

####################################################### User funtctions

def str2stdout(sourcestring, colors=None, title='', markup='html',
                 header=None, footer=None,
                 linenumbers=0, form=None):
    """Converts a code(string) to colorized HTML. Writes to stdout.

       form='code',or'snip' (for "<pre>yourcode</pre>" only)
       colors=null,mono,lite,dark,dark2,idle,or pythonwin
    """
    Parser(sourcestring, colors=colors, title=title, markup=markup,
           header=header, footer=footer,
           linenumbers=linenumbers).format(form)

def path2stdout(sourcepath, title='', colors=None, markup='html',
                   header=None, footer=None,
                   linenumbers=0, form=None):
    """Converts code(file) to colorized HTML. Writes to stdout.

       form='code',or'snip' (for "<pre>yourcode</pre>" only)
       colors=null,mono,lite,dark,dark2,idle,or pythonwin
    """
    sourcestring = open(sourcepath).read()
    Parser(sourcestring, colors=colors, title=sourcepath, 
           markup=markup, header=header, footer=footer,
           linenumbers=linenumbers).format(form)

def str2html(sourcestring, colors=None, title='', 
               markup='html', header=None, footer=None,
               linenumbers=0, form=None):
    """Converts a code(string) to colorized HTML. Returns an HTML string.

       form='code',or'snip' (for "<pre>yourcode</pre>" only)
       colors=null,mono,lite,dark,dark2,idle,or pythonwin
    """
    stringIO = StringIO.StringIO()
    Parser(sourcestring, colors=colors, title=title, out=stringIO,
           markup=markup, header=header, footer=footer,
           linenumbers=linenumbers).format(form)
    stringIO.seek(0)
    return stringIO.read()
  
def str2css(sourcestring, colors=None, title='',
              markup='css', header=None, footer=None,  
              linenumbers=0, form=None):
    """Converts a code string to colorized CSS/HTML. Returns CSS/HTML string
       
       If form != None then this will return (stylesheet_str, code_str)
       colors=null,mono,lite,dark,dark2,idle,or pythonwin
    """
    if markup.lower() not in ['css' ,'xhtml']:
        markup = 'css'
    stringIO = StringIO.StringIO()
    parse = Parser(sourcestring, colors=colors, title=title,
                   out=stringIO, markup=markup,
                   header=header, footer=footer,
                   linenumbers=linenumbers)
    parse.format(form)
    stringIO.seek(0)
    if form != None:
        return parse._sendCSSStyle(external=1), stringIO.read()
    else:
        return None, stringIO.read()

def str2markup(sourcestring, colors=None, title = '',
               markup='xhtml', header=None, footer=None, 
              linenumbers=0, form=None):
    """ Convert code strings into ([stylesheet or None], colorized string) """
    if markup.lower() == 'html':
        return None, str2html(sourcestring, colors=colors, title=title,
                   header=header, footer=footer, markup=markup, 
                   linenumbers=linenumbers, form=form)
    else:
        return str2css(sourcestring, colors=colors, title=title,
                   header=header, footer=footer, markup=markup, 
                   linenumbers=linenumbers, form=form)

def str2file(sourcestring, outfile, colors=None, title='', 
               markup='html', header=None, footer=None, 
               linenumbers=0, show=0, dosheet=1, form=None):
    """Converts a code string to a file.

       makes no attempt at correcting bad pathnames
    """
    css , html = str2markup(sourcestring, colors=colors, title='',
                    markup=markup, header=header, footer=footer,
                    linenumbers=linenumbers, form=form)
    # write html
    f = open(outfile,'wt')
    f.writelines(html)
    f.close()
    #write css
    if css != None and dosheet: 
        dir = os.path.dirname(outfile)
        outcss = os.path.join(dir,'pystyle.css')
        f = open(outcss,'wt')
        f.writelines(css)
        f.close()
    if show:
        showpage(outfile)

def path2html(sourcepath, colors=None, markup='html',
                header=None, footer=None,
                linenumbers=0, form=None):
    """Converts code(file) to colorized HTML. Returns an HTML string.

       form='code',or'snip' (for "<pre>yourcode</pre>" only)
       colors=null,mono,lite,dark,dark2,idle,or pythonwin
    """
    stringIO = StringIO.StringIO()
    sourcestring = open(sourcepath).read()
    Parser(sourcestring, colors, title=sourcepath, out=stringIO,
           markup=markup, header=header, footer=footer,
           linenumbers=linenumbers).format(form)
    stringIO.seek(0)
    return stringIO.read()

def convert(source, outdir=None, colors=None,
              show=0, markup='html', quiet=0,
              header=None, footer=None, linenumbers=0, form=None):
    """Takes a file or dir as input and places the html in the outdir.

       If outdir is none it defaults to the input dir
    """
    count=0
    # If it is a filename then path2file
    if not os.path.isdir(source):
        if os.path.isfile(source):
            count+=1
            path2file(source, outdir, colors, show, markup, 
                     quiet, form, header, footer, linenumbers, count)
        else:
            raise PathError, 'File does not exist!'
    # If we pass in a dir we need to walkdir for files.
    # Then we need to colorize them with path2file
    else:
        fileList = walkdir(source)
        if fileList != None:
            # make sure outdir is a dir
            if outdir != None:
                if os.path.splitext(outdir)[1] != '':
                    outdir = os.path.split(outdir)[0]
            for item in fileList:
                count+=1
                path2file(item, outdir, colors, show, markup,
                          quiet, form, header, footer, linenumbers, count)
            _printinfo('Completed colorizing %s files.'%str(count), quiet)
        else:
            _printinfo("No files to convert in dir.", quiet)

def path2file(sourcePath, out=None, colors=None, show=0,
                markup='html', quiet=0, form=None,
                header=None, footer=None, linenumbers=0, count=1):
    """ Converts python source to html file"""
    # If no outdir is given we use the sourcePath
    if out == None:#this is a guess
        htmlPath = sourcePath + '.html'
    else:
        # If we do give an out_dir, and it does
        # not exist , it will be created.
        if os.path.splitext(out)[1] == '':
            if not os.path.isdir(out):
                os.makedirs(out)
            sourceName = os.path.basename(sourcePath)
            htmlPath = os.path.join(out,sourceName)+'.html'
        # If we do give an out_name, and its dir does
        # not exist , it will be created.
        else:
            outdir = os.path.split(out)[0]
            if not os.path.isdir(outdir):
                os.makedirs(outdir)
            htmlPath = out
    htmlPath = os.path.abspath(htmlPath)
    # Open the text and do the parsing.
    source = open(sourcePath).read()
    parse = Parser(source, colors, sourcePath, open(htmlPath, 'wt'),
                   markup, header, footer, linenumbers)
    parse.format(form)
    _printinfo("  wrote %s" % htmlPath, quiet)
    # html markup will ignore the external flag, but
    # we need to stop the blank file from being written.
    if form == 'external' and count == 1 and markup != 'html':
        cssSheet = parse._sendCSSStyle(external=1)
        cssPath = os.path.join(os.path.dirname(htmlPath),'pystyle.css')
        css = open(cssPath, 'wt')
        css.write(cssSheet)
        css.close()
        _printinfo("    wrote %s" % cssPath, quiet)
    if show:
        # load HTML page into the default web browser.
        showpage(htmlPath)
    return htmlPath

def tagreplace(sourcestr, colors=lite, markup='xhtml', 
               linenumbers=0, dosheet=1, tagstart='<PY>'.lower(),
               tagend='</PY>'.lower(), stylesheet='pystyle.css'):
    """This is a helper function for pageconvert. Returns css, page.
    """
    if markup.lower() != 'html':
        link  = '<link rel="stylesheet" href="%s" type="text/css"/></head>'
        css = link%stylesheet
        if sourcestr.find(css) == -1:
            sourcestr = sourcestr.replace('</head>', css, 1)
    starttags = sourcestr.count(tagstart)
    endtags = sourcestr.count(tagend)
    if starttags:
        if starttags == endtags:
            for _ in range(starttags):
               datastart = sourcestr.find(tagstart)
               dataend = sourcestr.find(tagend)
               data = sourcestr[datastart+len(tagstart):dataend]
               data = unescape(data)
               css , data = str2markup(data, colors=colors, 
                         linenumbers=linenumbers, markup=markup, form='embed')
               start = sourcestr[:datastart]
               end = sourcestr[dataend+len(tagend):]
               sourcestr =  ''.join([start,data,end])
        else:
            raise InputError,'Tag mismatch!\nCheck %s,%s tags'%tagstart,tagend
    if not dosheet:
        css = None
    return css, sourcestr
    
def pageconvert(path, out=None, colors=lite, markup='xhtml', linenumbers=0,
                  dosheet=1, tagstart='<PY>'.lower(), tagend='</PY>'.lower(),
                  stylesheet='pystyle', show=1, returnstr=0):
    """This function can colorize Python source

       that is written in a webpage enclosed in tags.
    """
    if out == None:
        out = os.path.dirname(path)
    infile = open(path, 'r').read()
    css,page  = tagreplace(sourcestr=infile,colors=colors, 
                   markup=markup, linenumbers=linenumbers, dosheet=dosheet,
                   tagstart=tagstart, tagend=tagend, stylesheet=stylesheet)
    if not returnstr:
        newpath = os.path.abspath(os.path.join(
                  out,'tmp', os.path.basename(path)))
        if not os.path.exists(newpath):
            try:
                os.makedirs(os.path.dirname(newpath))
            except:
                pass#traceback.print_exc()
                #Usage()
        y = open(newpath, 'w')
        y.write(page)
        y.close()
        if css:
            csspath = os.path.abspath(os.path.join(
                      out,'tmp','%s.css'%stylesheet))
            x = open(csspath,'w')
            x.write(css)
            x.close()
        if show:
            try:
                os.startfile(newpath)
            except:
                traceback.print_exc()
        return newpath
    else:
        return css, page

##################################################################### helpers

def walkdir(dir):
    """Return a list of .py and .pyw files from a given directory.

       This function can be written as a generator Python 2.3, or a genexp
       in Python 2.4. But 2.2 and 2.1 would be left out....
    """
    # Get a list of files that match *.py*
    GLOB_PATTERN = os.path.join(dir, "*.[p][y]*")
    pathlist = glob.glob(GLOB_PATTERN)
    # Now filter out all but py and pyw
    filterlist = [x for x in pathlist
                        if x.endswith('.py')
                        or x.endswith('.pyw')]
    if filterlist != []:
        # if we have a list send it
        return filterlist
    else:
        return None

def showpage(path):
    """Helper function to open webpages"""
    try:
        import webbrowser
        webbrowser.open_new(os.path.abspath(path))
    except:
        traceback.print_exc()

def _printinfo(message, quiet):
    """Helper to print messages"""
    if not quiet:
        print message

def escape(text):
     """escape text for html. similar to cgi.escape"""
     text = text.replace("&", "&amp;")
     text = text.replace("<", "&lt;")
     text = text.replace(">", "&gt;")
     return text

def unescape(text):
     """unsecape escaped text"""
     text = text.replace("&quot;", '"')
     text = text.replace("&gt;", ">")
     text = text.replace("&lt;", "<")
     text = text.replace("&amp;", "&")
     return text

########################################################### Custom Exceptions

class PySourceColorError(Exception):
    # Base for custom errors
    def __init__(self, msg=''):
        self._msg = msg
        Exception.__init__(self, msg)
    def __repr__(self):
        return self._msg
    __str__ = __repr__

class PathError(PySourceColorError):
    def __init__(self, msg):
       PySourceColorError.__init__(self,
         'Path error! : %s'% msg)

class InputError(PySourceColorError):
   def __init__(self, msg):
       PySourceColorError.__init__(self,
         'Input error! : %s'% msg)

########################################################## Python code parser

class Parser(object):

    """MoinMoin python parser heavily chopped :)"""

    def __init__(self, raw, colors=None, title='', out=sys.stdout,
                   markup='html', header=None, footer=None, linenumbers=0):
        """Store the source text & set some flags"""
        if colors == None:
            colors = defaultColors
        self.raw = raw.expandtabs().rstrip()
        self.title = os.path.basename(title)
        self.out = out
        self.line = ''
        self.lasttext = ''
        self.argFlag = 0
        self.classFlag = 0
        self.defFlag = 0
        self.decoratorFlag = 0
        self.external = 0
        self.markup = markup.upper()
        self.colors = colors
        self.header = header
        self.footer = footer
        self.doArgs = 1 #  overrides the new tokens
        self.doNames = 1 #  overrides the new tokens
        self.doMathOps = 1 #  overrides the new tokens
        self.doBrackets = 1 #  overrides the new tokens
        self.doURL = 1 # override url conversion
        self.LINENUMHOLDER = "___line___".upper()
        self.LINESTART = "___start___".upper()
        self.skip = 0
        # add space left side of code for padding.Override in color dict.
        self.extraspace = self.colors.get(EXTRASPACE, '')
        # Linenumbers less then zero also have numberlinks
        self.dolinenums = self.linenum = abs(linenumbers)
        if linenumbers < 0:
            self.numberlinks = 1
        else:
            self.numberlinks = 0

    def format(self, form=None):
        """Parse and send the colorized source"""
        if form in ('snip','code'):
            self.addEnds = 0
        elif form == 'embed':
            self.addEnds = 0
            self.external = 1
        else:
            if form == 'external':
                self.external = 1
            self.addEnds = 1

        # Store line offsets in self.lines
        self.lines = [0, 0]
        pos = 0

        # Add linenumbers
        if self.dolinenums:
            start=self.LINENUMHOLDER+' '+self.extraspace
        else:
            start=''+self.extraspace
        newlines = []
        lines = self.raw.splitlines(0)
        for l in lines:
             # span and div escape for customizing and embedding raw text 
             if (l.startswith('#$#')
                  or l.startswith('#%#')
                  or l.startswith('#@#')):   
                newlines.append(l)
             else:
                # kludge for line spans in css,xhtml
                if self.markup in ['XHTML','CSS']:
                    newlines.append(self.LINESTART+' '+start+l)
                else:
                    newlines.append(start+l)
        self.raw = "\n".join(newlines)+'\n'# plus an extra newline at the end

        # Gather lines
        while 1:
            pos = self.raw.find('\n', pos) + 1
            if not pos: break
            self.lines.append(pos)
        self.lines.append(len(self.raw))

        # Wrap text in a filelike object
        self.pos = 0
        text = StringIO.StringIO(self.raw)
        
        # Markup start
        if self.addEnds:
            self._doPageStart()
        else:
            self._doSnippetStart()

        ## Tokenize calls the __call__
        ## function for each token till done.
        # Parse the source and write out the results.
        try:
            tokenize.tokenize(text.readline, self)
        except tokenize.TokenError, ex:
            msg = ex[0]
            line = ex[1][0]
            self.out.write("<h3>ERROR: %s</h3>%s\n"%
                            (msg, self.raw[self.lines[line]:]))
            #traceback.print_exc()

        # Markup end
        if self.addEnds:
            self._doPageEnd()
        else:
            self._doSnippetEnd()

    def __call__(self, toktype, toktext, (srow,scol), (erow,ecol), line):
        """Token handler. Order is important do not rearrange."""
        self.line = line
        # Calculate new positions
        oldpos = self.pos
        newpos = self.lines[srow] + scol
        self.pos = newpos + len(toktext)
        # Handle newlines
        if toktype in (token.NEWLINE, tokenize.NL):
            self.decoratorFlag = self.argFlag = 0
            # kludge for line spans in css,xhtml
            if self.markup in ['XHTML','CSS']:
                self.out.write('</span>')
            self.out.write('\n')
            return

        # Send the original whitespace, and tokenize backslashes if present.
        # Tokenizer.py just sends continued line backslashes with whitespace.
        # This is a hack to tokenize continued line slashes as operators.
        # Should continued line backslashes be treated as operators
        # or some other token?

        if newpos > oldpos:
            if self.raw[oldpos:newpos].isspace():
                # consume a single space after linestarts and linenumbers
                # had to have them so tokenizer could seperate them.
                # multiline strings are handled by do_Text functions
                if self.lasttext != self.LINESTART \
                        and self.lasttext != self.LINENUMHOLDER:
                    self.out.write(self.raw[oldpos:newpos])
                else:
                    self.out.write(self.raw[oldpos+1:newpos])
            else:
                slash = self.raw[oldpos:newpos].find('\\')+oldpos
                self.out.write(self.raw[oldpos:slash])
                getattr(self, '_send%sText'%(self.markup))(OPERATOR, '\\')
                self.linenum+=1
                # kludge for line spans in css,xhtml
                if self.markup in ['XHTML','CSS']:
                    self.out.write('</span>')
                self.out.write(self.raw[slash+1:newpos])

        # Skip indenting tokens
        if toktype in (token.INDENT, token.DEDENT):
            self.pos = newpos
            return

        # Look for operators
        if token.LPAR <= toktype and toktype <= token.OP:
            # Trap decorators py2.4 >
            if toktext == '@':
                toktype = DECORATOR
                # Set a flag if this was the decorator start so
                # the decorator name and arguments can be identified
                self.decoratorFlag = self.argFlag = 1
            else:
                if self.doArgs:
                    # Find the start for arguments
                    if toktext == '(' and self.argFlag:
                        self.argFlag = 2
                    # Find the end for arguments
                    elif toktext == ':':
                        self.argFlag = 0
                ## Seperate the diffrent operator types
                # Brackets
                if self.doBrackets and toktext in ['[',']','(',')','{','}']:
                    toktype = BRACKETS
                # Math operators 
                elif self.doMathOps and toktext in ['*=','**=','-=','+=','|=',
                                                      '%=','>>=','<<=','=','^=',
                                                      '/=', '+','-','**','*','/','%']:
                    toktype = MATH_OPERATOR
                # Operator 
                else:
                    toktype = OPERATOR
                    # example how flags should work.
                    # def fun(arg=argvalue,arg2=argvalue2):
                    # 0   1  2 A 1   N    2 A  1    N     0
                    if toktext == "=" and self.argFlag == 2:
                         self.argFlag = 1
                    elif toktext == "," and self.argFlag == 1:
                        self.argFlag = 2
        # Look for keywords
        elif toktype == NAME and keyword.iskeyword(toktext):
            toktype = KEYWORD
            # Set a flag if this was the class / def start so
            # the class / def name and arguments can be identified
            if toktext in ['class', 'def']:
                if toktext =='class' and \
                         not line[:line.find('class')].endswith('.'): 
                    self.classFlag = self.argFlag = 1
                elif toktext == 'def' and \
                         not line[:line.find('def')].endswith('.'):
                    self.defFlag = self.argFlag = 1
                else:
                    # must have used a keyword as a name i.e. self.class
                    toktype = ERRORTOKEN 

        # Look for class, def, decorator name
        elif (self.classFlag or self.defFlag or self.decoratorFlag) \
                and self.doNames:
            if self.classFlag:
                self.classFlag = 0
                toktype = CLASS_NAME
            elif self.defFlag:
                self.defFlag = 0
                toktype = DEF_NAME
            elif self.decoratorFlag:
                self.decoratorFlag = 0
                toktype = DECORATOR_NAME

        # Look for strings
        # Order of evaluation is important do not change.
        elif toktype == token.STRING:
            text = toktext.lower()
            # TRIPLE DOUBLE QUOTE's
            if (text[:3] == '"""'):
                toktype = TRIPLEDOUBLEQUOTE
            elif (text[:4] == 'r"""'):
                toktype = TRIPLEDOUBLEQUOTE_R
            elif (text[:4] == 'u"""' or
                   text[:5] == 'ur"""'):
                toktype = TRIPLEDOUBLEQUOTE_U
            # DOUBLE QUOTE's
            elif (text[:1] == '"'):
                toktype = DOUBLEQUOTE
            elif (text[:2] == 'r"'):
                toktype = DOUBLEQUOTE_R
            elif (text[:2] == 'u"' or
                   text[:3] == 'ur"'):
                toktype = DOUBLEQUOTE_U
            # TRIPLE SINGLE QUOTE's
            elif (text[:3] == "'''"):
                 toktype = TRIPLESINGLEQUOTE
            elif (text[:4] == "r'''"):
                toktype = TRIPLESINGLEQUOTE_R
            elif (text[:4] == "u'''" or
                   text[:5] == "ur'''"):
                toktype = TRIPLESINGLEQUOTE_U
            # SINGLE QUOTE's
            elif (text[:1] == "'"):
                toktype = SINGLEQUOTE
            elif (text[:2] == "r'"):
                toktype = SINGLEQUOTE_R
            elif (text[:2] == "u'" or
                   text[:3] == "ur'"):
                toktype = SINGLEQUOTE_U

            # test for invalid string declaration
            if self.lasttext.lower() == 'ru':
                toktype = ERRORTOKEN
           
        # Look for comments
        elif toktype == COMMENT:
            if toktext[:2] == "##":
                toktype = DOUBLECOMMENT
            elif toktext[:3] == '#$#':
                toktype = TEXT
                self.textFlag = 'SPAN'
                toktext = toktext[3:]
            elif toktext[:3] == '#%#':
                toktype = TEXT
                self.textFlag = 'DIV'
                toktext = toktext[3:]
            elif toktext[:3] == '#@#':
                toktype = TEXT
                self.textFlag = 'RAW'
                toktext = toktext[3:]
            if self.doURL:
                # this is a 'fake helper function'
                # url(URI,Alias_name) or url(URI)
                url_pos = toktext.find('url(')
                if url_pos != -1:
                    before = toktext[:url_pos]
                    url = toktext[url_pos+4:]
                    splitpoint = url.find(',')
                    endpoint = url.find(')')
                    after = url[endpoint+1:]
                    url = url[:endpoint]
                    if splitpoint != -1:
                        urlparts = url.split(',',1)
                        toktext = '%s<a href="%s">%s</a>%s'%(
                                   before,urlparts[0],urlparts[1].lstrip(),after) 
                    else:
                        toktext = '%s<a href="%s">%s</a>%s'%(before,url,url,after) 
                        
        # Seperate errors from decorators
        elif toktype == ERRORTOKEN:
            # Bug fix for < py2.4
            # space between decorators
            if self.argFlag and toktext.isspace():
                #toktype = NAME
                self.out.write(toktext)
                return
            # Bug fix for py2.2 linenumbers with decorators
            elif toktext.isspace():
                # What if we have a decorator after a >>> or ...
                #p = line.find('@')
                #if p >= 0 and not line[:p].isspace():
                    #self.out.write(toktext)
                    #return
                if self.skip:
                    self.skip=0
                    return
                else:           
                    self.out.write(toktext)
                    return
            # trap decorators < py2.4
            elif toktext == '@':
                toktype = DECORATOR
                # Set a flag if this was the decorator start so
                # the decorator name and arguments can be identified
                self.decoratorFlag = self.argFlag = 1

        # Seperate args from names
        elif (self.argFlag == 2 and
              toktype == NAME and
              toktext != 'None' and
              self.doArgs):
            toktype = ARGS

        # Look for line numbers
        # The conversion code for them is in the send_text functions.
        if toktext in [self.LINENUMHOLDER,self.LINESTART]:
            toktype = LINENUMBER
            # if we don't have linenumbers set flag
            # to skip the trailing space from linestart
            if toktext == self.LINESTART and not self.dolinenums \
                                or toktext == self.LINENUMHOLDER:
                self.skip=1


        # Skip blank token that made it thru
        ## bugfix for the last empty tag.
        if toktext == '':
            return

        # Last token text history
        self.lasttext = toktext
        
        # escape all but the urls in the comments
        if toktype in (DOUBLECOMMENT, COMMENT):
            if toktext.find('<a href=') == -1:
                toktext = escape(toktext)
            else:
                pass
        elif toktype == TEXT:
            pass
        else:
            toktext = escape(toktext)

        # Send text for any markup
        getattr(self, '_send%sText'%(self.markup))(toktype, toktext)
        return

    ################################################################# Helpers

    def _doSnippetStart(self):
        if self.markup == 'HTML':
            # Start of html snippet
            self.out.write('<pre>\n')
        else:
            # Start of css/xhtml snippet
            self.out.write(self.colors.get(CODESTART,'<pre class="py">\n'))

    def _doSnippetEnd(self):
        # End of html snippet
        self.out.write(self.colors.get(CODEEND,'</pre>\n'))

    ######################################################## markup selectors

    def _getFile(self, filepath): 
        try:
            _file = open(filepath,'r')
            content = _file.read()
            _file.close()
        except:
            traceback.print_exc()
            content = ''
        return content

    def _doPageStart(self):
        getattr(self, '_do%sStart'%(self.markup))()

    def _doPageHeader(self):
        if self.header != None:
            if self.header.find('#$#') != -1 or \
                self.header.find('#$#') != -1 or \
                self.header.find('#%#') != -1:
                self.out.write(self.header[3:])
            else:
                if self.header != '':
                    self.header = self._getFile(self.header)
                getattr(self, '_do%sHeader'%(self.markup))()

    def _doPageFooter(self):
        if self.footer != None:
            if self.footer.find('#$#') != -1 or \
                self.footer.find('#@#') != -1 or \
                self.footer.find('#%#') != -1:
                self.out.write(self.footer[3:])
            else:
                if self.footer != '':
                    self.footer = self._getFile(self.footer)
                getattr(self, '_do%sFooter'%(self.markup))()

    def _doPageEnd(self):
        getattr(self, '_do%sEnd'%(self.markup))()

    ################################################### color/style retrieval
    ## Some of these are not used anymore but are kept for documentation

    def _getLineNumber(self):
        num = self.linenum
        self.linenum+=1
        return  str(num).rjust(5)+" "

    def _getTags(self, key):
        # style tags
        return self.colors.get(key, self.colors[NAME])[0]

    def _getForeColor(self, key):
        # get text foreground color, if not set to black
        color = self.colors.get(key, self.colors[NAME])[1]
        if color[:1] != '#':
            color = '#000000'
        return color

    def _getBackColor(self, key):
        # get text background color
        return self.colors.get(key, self.colors[NAME])[2]

    def _getPageColor(self):
        # get page background color
        return self.colors.get(PAGEBACKGROUND, '#FFFFFF')

    def _getStyle(self, key):
        # get the token style from the color dictionary
        return self.colors.get(key, self.colors[NAME])

    def _getMarkupClass(self, key):
        # get the markup class name from the markup dictionary
        return MARKUPDICT.get(key, MARKUPDICT[NAME])

    def _getDocumentCreatedBy(self):
        return '<!--This document created by %s ver.%s on: %s-->\n'%(
                  __title__,__version__,time.ctime())

    ################################################### HTML markup functions

    def _doHTMLStart(self):
        # Start of html page
        self.out.write('<!DOCTYPE html PUBLIC \
"-//W3C//DTD HTML 4.01//EN">\n')
        self.out.write('<html><head><title>%s</title>\n'%(self.title))
        self.out.write(self._getDocumentCreatedBy())
        self.out.write('<meta http-equiv="Content-Type" \
content="text/html;charset=iso-8859-1">\n')
        # Get background
        self.out.write('</head><body bgcolor="%s">\n'%self._getPageColor())
        self._doPageHeader()
        self.out.write('<pre>')

    def _getHTMLStyles(self, toktype, toktext):
        # Get styles
        tags, color = self.colors.get(toktype, self.colors[NAME])[:2]#
        tagstart=[]
        tagend=[]
        # check for styles and set them if needed.
        if 'b' in tags:#Bold
            tagstart.append('<b>')
            tagend.append('</b>')
        if 'i' in tags:#Italics
            tagstart.append('<i>')
            tagend.append('</i>')
        if 'u' in tags:#Underline
            tagstart.append('<u>')
            tagend.append('</u>')
        # HTML tags should be paired like so : <b><i><u>Doh!</u></i></b>
        tagend.reverse()
        starttags="".join(tagstart)
        endtags="".join(tagend)
        return starttags,endtags,color

    def _sendHTMLText(self, toktype, toktext):
        numberlinks = self.numberlinks
        
        # If it is an error, set a red box around the bad tokens
        # older browsers should ignore it
        if toktype == ERRORTOKEN:
            style = ' style="border: solid 1.5pt #FF0000;"'
        else:
            style = ''
        # Get styles
        starttag, endtag, color = self._getHTMLStyles(toktype, toktext)
        # This is a hack to 'fix' multi-line  strings.
        # Multi-line strings are treated as only one token 
        # even though they can be several physical lines.
        # That makes it hard to spot the start of a line,
        # because at this level all we know about are tokens.
        
        if toktext.count(self.LINENUMHOLDER):
            # rip apart the string and separate it by line.
            # count lines and change all linenum token to line numbers.
            # embedded all the new font tags inside the current one.
            # Do this by ending the tag first then writing our new tags,
            # then starting another font tag exactly like the first one.
            if toktype == LINENUMBER:
                splittext = toktext.split(self.LINENUMHOLDER)
            else:    
                splittext = toktext.split(self.LINENUMHOLDER+' ')
            store = []
            store.append(splittext.pop(0))
            lstarttag, lendtag, lcolor = self._getHTMLStyles(LINENUMBER, toktext)
            count = len(splittext)
            for item in splittext:
                num =  self._getLineNumber()
                if numberlinks:
                    numstrip = num.strip()
                    content = '<a name="%s" href="#%s">%s</a>' \
                              %(numstrip,numstrip,num)
                else:
                    content = num
                if count <= 1:
                    endtag,starttag = '',''
                linenumber = ''.join([endtag,'<font color=', lcolor, '>',
                            lstarttag, content, lendtag, '</font>' ,starttag])
                store.append(linenumber+item)
            toktext = ''.join(store)
        # send text
        ## Output optimization
        # skip font tag if black text, but styles will still be sent. (b,u,i)
        if color !='#000000':
            startfont = '<font color="%s"%s>'%(color, style)
            endfont = '</font>'
        else:
            startfont, endfont = ('','')
        if toktype != LINENUMBER:
            self.out.write(''.join([startfont,starttag,
                                     toktext,endtag,endfont]))
        else:
            self.out.write(toktext)
        return

    def _doHTMLHeader(self):
        # Optional
        if self.header != '':
            self.out.write('%s\n'%self.header)
        else:
            color = self._getForeColor(NAME)
            self.out.write('<b><font color="%s"># %s \
                            <br># %s</font></b><hr>\n'%
                           (color, self.title, time.ctime()))

    def _doHTMLFooter(self):
        # Optional
        if self.footer != '':
            self.out.write('%s\n'%self.footer)
        else:
            color = self._getForeColor(NAME)
            self.out.write('<b><font color="%s"> \
                            <hr># %s<br># %s</font></b>\n'%
                           (color, self.title, time.ctime()))

    def _doHTMLEnd(self):
        # End of html page
        self.out.write('</pre>\n')
        # Write a little info at the bottom
        self._doPageFooter()
        self.out.write('</body></html>\n')

    #################################################### CSS markup functions

    def _getCSSStyle(self, key):
        # Get the tags and colors from the dictionary
        tags, forecolor, backcolor = self._getStyle(key)
        style=[]
        border = None
        bordercolor = None
        tags = tags.lower()
        if tags:
            # get the border color if specified
            # the border color will be appended to
            # the list after we define a border
            if '#' in tags:# border color 
                start = tags.find('#')
                end = start + 7
                bordercolor = tags[start:end]
                tags.replace(bordercolor,'',1)
            # text styles
            if 'b' in tags:# Bold
                style.append('font-weight:bold;')
            else:
                style.append('font-weight:normal;')    
            if 'i' in tags:# Italic
                style.append('font-style:italic;')
            if 'u' in tags:# Underline
                style.append('text-decoration:underline;')
            # border size
            if 'l' in tags:# thick border
                size='thick'
            elif 'm' in tags:# medium border
                size='medium'
            elif 't' in tags:# thin border
                size='thin'
            else:# default
                size='medium'
            # border styles
            if 'n' in tags:# inset border
                border='inset'
            elif 'o' in tags:# outset border
                border='outset'
            elif 'r' in tags:# ridge border
                border='ridge'
            elif 'g' in tags:# groove border
                border='groove'
            elif '=' in tags:# double border
                border='double'
            elif '.' in tags:# dotted border
                border='dotted'
            elif '-' in tags:# dashed border
                border='dashed'
            elif 's' in tags:# solid border 
                border='solid'
            # border type check
            seperate_sides=0
            for side in ['<','>','^','v']:
                if side in tags:
                    seperate_sides+=1
            # border box or seperate sides
            if seperate_sides==0 and border:
                    style.append('border: %s %s;'%(border,size))
            else:
                if border == None:
                   border = 'solid'
                if 'v' in tags:# bottom border
                    style.append('border-bottom:%s %s;'%(border,size))
                if '<' in tags:# left border
                    style.append('border-left:%s %s;'%(border,size))
                if '>' in tags:# right border
                    style.append('border-right:%s %s;'%(border,size))
                if '^' in tags:# top border
                    style.append('border-top:%s %s;'%(border,size))
        else:
            style.append('font-weight:normal;')# css inherited style fix    
        # we have to define our borders before we set colors
        if bordercolor:
            style.append('border-color:%s;'%bordercolor)
        # text forecolor  
        style.append('color:%s;'% forecolor)
        # text backcolor
        if backcolor:
            style.append('background-color:%s;'%backcolor)
        return (self._getMarkupClass(key),' '.join(style))

    def _sendCSSStyle(self, external=0):
        """ create external and internal style sheets"""
        styles = []
        external += self.external
        if not external:
            styles.append('<style type="text/css">\n<!--\n')
        # Get page background color and write styles ignore any we don't know
        styles.append('body { background:%s; }\n'%self._getPageColor())
        # write out the various css styles
        for key in MARKUPDICT:
            styles.append('.%s { %s }\n'%self._getCSSStyle(key))
        # If you want to style the pre tag you must modify the color dict.
        #  Example: 
        #  lite[PY] = .py {border: solid thin #000000;background:#555555}\n''' 
        styles.append(self.colors.get(PY, '.py { }\n'))
        # Extra css can be added here
        # add CSSHOOK to the color dict if you need it.
        # Example: 
        #lite[CSSHOOK] = """.mytag { border: solid thin #000000; } \n
        #                   .myothertag { font-weight:bold; )\n"""
        styles.append(self.colors.get(CSSHOOK,''))
        if not self.external:
             styles.append('--></style>\n')
        return ''.join(styles)

    def _doCSSStart(self):
        # Start of css/html 4.01 page
        self.out.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN">\n')
        self.out.write('<html><head><title>%s</title>\n'%(self.title))
        self.out.write(self._getDocumentCreatedBy())
        self.out.write('<meta http-equiv="Content-Type" \
content="text/html;charset=iso-8859-1">\n')
        self._doCSSStyleSheet()
        self.out.write('</head>\n<body>\n')
        # Write a little info at the top.
        self._doPageHeader()
        self.out.write(self.colors.get(CODESTART,'<pre class="py">\n'))
        return

    def _doCSSStyleSheet(self):
        if not self.external:
            # write an embedded style sheet
            self.out.write(self._sendCSSStyle())
        else:
            # write a link to an external style sheet
            self.out.write('<link rel="stylesheet" \
href="pystyle.css" type="text/css">')
        return

    def _sendCSSText(self, toktype, toktext):
        # This is a hack to 'fix' multi-line strings.
        # Multi-line strings are treated as only one token 
        # even though they can be several physical lines.
        # That makes it hard to spot the start of a line,
        # because at this level all we know about are tokens.
        markupclass = MARKUPDICT.get(toktype, MARKUPDICT[NAME])
        # if it is a LINENUMBER type then we can skip the rest
        if toktext == self.LINESTART and toktype == LINENUMBER:
            self.out.write('<span class="py_line">')
            return
        if toktext.count(self.LINENUMHOLDER):
            # rip apart the string and separate it by line
            # count lines and change all linenum token to line numbers
            # also convert linestart and lineend tokens
            # <linestart> <lnumstart> lnum <lnumend> text <lineend>
            #################################################
            newmarkup = MARKUPDICT.get(LINENUMBER, MARKUPDICT[NAME])
            lstartspan = '<span class="%s">'%(newmarkup)
            if toktype == LINENUMBER:
                splittext = toktext.split(self.LINENUMHOLDER)
            else:    
                splittext = toktext.split(self.LINENUMHOLDER+' ')
            store = []
            # we have already seen the first linenumber token
            # so we can skip the first one
            store.append(splittext.pop(0))
            for item in splittext:
                num = self._getLineNumber()
                if self.numberlinks:
                    numstrip = num.strip()
                    content= '<a name="%s" href="#%s">%s</a>' \
                              %(numstrip,numstrip,num)
                else:
                    content = num
                linenumber= ''.join([lstartspan,content,'</span>'])
                store.append(linenumber+item)
            toktext = ''.join(store)
        if toktext.count(self.LINESTART):
            # wraps the textline in a line span
            # this adds a lot of kludges, is it really worth it?
            store = []
            parts = toktext.split(self.LINESTART+' ')
            # handle the first part differently
            # the whole token gets wraqpped in a span later on
            first = parts.pop(0)
            # place spans before the newline
            pos = first.rfind('\n')
            if pos != -1:
                first=first[:pos]+'</span></span>'+first[pos:]
            store.append(first)
            #process the rest of the string
            for item in parts:
                #handle line numbers if present
                if self.dolinenums:
                    item = item.replace('</span>',
                           '</span><span class="%s">'%(markupclass))
                else:
                    item = '<span class="%s">%s'%(markupclass,item)
                # add endings for line and string tokens
                pos = item.rfind('\n')
                if pos != -1:
                    item=item[:pos]+'</span></span>\n'
                store.append(item)
            # add start tags for lines
            toktext = '<span class="py_line">'.join(store)
        # Send text
        if toktype != LINENUMBER:
            if toktype == TEXT and self.textFlag == 'DIV':
                startspan = '<div class="%s">'%(markupclass)
                endspan = '</div>'
            elif toktype == TEXT and self.textFlag == 'RAW': 
                startspan,endspan = ('','')
            else:
                startspan = '<span class="%s">'%(markupclass)
                endspan = '</span>'
            self.out.write(''.join([startspan, toktext, endspan]))
        else:
            self.out.write(toktext)
        return

    def _doCSSHeader(self):
        if self.header != '':
            self.out.write('%s\n'%self.header)
        else:
            name = MARKUPDICT.get(NAME)
            self.out.write('<div class="%s"># %s <br> \
# %s</div><hr>\n'%(name, self.title, time.ctime()))

    def _doCSSFooter(self):
        # Optional
        if self.footer != '':
            self.out.write('%s\n'%self.footer)
        else:
            self.out.write('<hr><div class="%s"># %s <br> \
# %s</div>\n'%(MARKUPDICT.get(NAME),self.title, time.ctime()))

    def _doCSSEnd(self):
        # End of css/html page
        self.out.write(self.colors.get(CODEEND,'</pre>\n'))
        # Write a little info at the bottom
        self._doPageFooter()
        self.out.write('</body></html>\n')
        return

    ################################################## XHTML markup functions

    def _doXHTMLStart(self):
        # XHTML is really just XML + HTML 4.01.
        # We only need to change the page headers, 
        # and a few tags to get valid XHTML.
        # Start of xhtml page
        self.out.write('<?xml version="1.0"?>\n \
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"\n \
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n \
<html xmlns="http://www.w3.org/1999/xhtml">\n')
        self.out.write('<head><title>%s</title>\n'%(self.title))
        self.out.write(self._getDocumentCreatedBy())
        self.out.write('<meta http-equiv="Content-Type" \
content="text/html;charset=iso-8859-1"/>\n')
        self._doXHTMLStyleSheet()
        self.out.write('</head>\n<body>\n')
        # Write a little info at the top.
        self._doPageHeader()
        self.out.write(self.colors.get(CODESTART,'<pre class="py">\n'))
        return

    def _doXHTMLStyleSheet(self):
        if not self.external:
            # write an embedded style sheet
            self.out.write(self._sendCSSStyle())
        else:
            # write a link to an external style sheet
            self.out.write('<link rel="stylesheet" \
href="pystyle.css" type="text/css"/>\n')
        return

    def _sendXHTMLText(self, toktype, toktext):
        self._sendCSSText(toktype, toktext)

    def _doXHTMLHeader(self):
        # Optional
        if self.header:
            self.out.write('%s\n'%self.header)
        else:
            name = MARKUPDICT.get(NAME)
            self.out.write('<div class="%s"># %s <br/> \
# %s</div><hr/>\n '%(
            name, self.title, time.ctime()))

    def _doXHTMLFooter(self):
        # Optional
        if self.footer:
            self.out.write('%s\n'%self.footer)
        else:
            self.out.write('<hr/><div class="%s"># %s <br/> \
# %s</div>\n'%(MARKUPDICT.get(NAME), self.title, time.ctime()))

    def _doXHTMLEnd(self):
        self._doCSSEnd()

#############################################################################

if __name__ == '__main__':
    cli()

#############################################################################
# PySourceColor.py
# 2004, 2005 M.E.Farmer Jr.
# Python license
