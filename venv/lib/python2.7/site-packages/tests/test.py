# -*- coding: utf-8 -*-
import random, unittest, re
from pairtree import PairtreeStorageClient

from pairtree import ppath


PAIRTREE_STORAGE_DIR = "/tmp/pairtree"

class TestPairtree(unittest.TestCase):
    def i2p2i(self, id, target, label):
        ppath = self.pairtree._id_to_dir_list(id)[1:]
        self.assertEqual(ppath, target)
        #self.assertEqual( reverse it)

    def roundtrip(self, id, label):
        ppath = self.pairtree.id_encode(id)
        new_id = self.pairtree.id_decode(ppath)
        self.assertEqual(id, new_id)
        self.ppath_roundtrip(id, label)
        #self.assertEqual( reverse it)

    def ppath_roundtrip(self, id, label):
        pp = ppath.get_id_from_dirpath(ppath.id_to_dirpath(id))
        self.assertEqual(pp, id)

    def setUp(self):
        self.pairtree = PairtreeStorageClient('http://example.org', PAIRTREE_STORAGE_DIR, 2)

    def test_empty(self):
        pass
        #try:
        #    ppath = PairPath("")
        #    self.assertFalse(True, 'Empty id should raise exception')
        #except BadPairPath:
        #    pass

    def testabc(self):
        self.i2p2i('abc', ['ab','c','obj'], 'basic 3-char case')
    
    def testabc_roundtrip(self):
        self.roundtrip('abc', 'basic 3-char case - roundtrip')

    def testabc(self):
        self.i2p2i('abcd', ['ab','cd', 'obj'], 'basic 4-char case')

    def testabc_roundtrip(self):
        self.roundtrip('abcd', 'basic 4-char case - roundtrip')
    
    def testabc(self):
        self.i2p2i('abcd', ['ab','cd', 'obj'], 'basic 4-char case')
        
    def testabc_roundtrip(self):
        self.roundtrip('abcd', 'basic 4-char case - roundtrip')

    def testxy(self):
        self.i2p2i('xy', ['xy', 'obj'], '2-char edge case')
        
    def testxy_roundtrip(self):
        self.roundtrip('xy', '2-char edge case - roundtrip')

    def testz(self):
        self.i2p2i('z', ['z', 'obj'], '1-char edge case')
        
    def testz_roundtrip(self):
        self.roundtrip('z', '1-char edge case - roundtrip')
        
    def test12_986xy4(self):
        self.i2p2i('12-986xy4', ['12', '-9', '86', 'xy', '4', 'obj'], 'hyphen')
        
    def test12_986xy4_roundtrip(self):
        self.roundtrip('12-986xy4', 'hyphen - roundtrip')

    def test_13030_45xqv_793842495(self):
        self.i2p2i('13030_45xqv_793842495',
                   ['13', '03', '0_', '45', 'xq', 'v_', '79', '38', '42', '49', 
                    '5', 'obj'],
                   'long id with undescores')

    def test_13030_45xqv_793842495_roundtrip(self):
        self.roundtrip('13030_45xqv_793842495',
                   'long id with undescores - roundtrip')

    def test_ark_13030_xt12t3(self):
        self.i2p2i('ark:/13030/xt12t3',
                   ['ar', 'k+', '=1', '30', '30', '=x', 't1', '2t', '3', 'obj'],
                   'colons and slashes')

    def test_ark_13030_xt12t3_roundtrip(self):
        self.roundtrip('ark:/13030/xt12t3',
                   'colons and slashes - roundtrip')

    def test_space(self):
        self.i2p2i('hello world', ['he', 'll', 'o^', '20', 'wo', 'rl', 'd', 'obj'], 'space')
        
    def test_space_roundtrip(self):
        self.roundtrip('hello world', 'space - roundtrip')
        
    def test_slash(self):
        self.i2p2i('/', ['=', 'obj'], '1-separator-char edge case')

    def test_slash_roundtrip(self):
        self.roundtrip('/', '1-separator-char edge case - roundtrip')

    def test_urn(self):
        self.i2p2i('http://n2t.info/urn:nbn:se:kb:repos-1',
                   ['ht', 'tp', '+=', '=n', '2t', ',i', 'nf', 'o=', 'ur', 'n+', 
                    'nb', 'n+', 'se', '+k', 'b+', 're', 'po', 's-', '1', 'obj'],
                   'a URL with colons, slashes, and periods')

    def test_urn_roundtrip(self):
        self.roundtrip('http://n2t.info/urn:nbn:se:kb:repos-1',
                   'a URL with colons, slashes, and periods - roundtrip')

    def test_wtf(self):
        self.i2p2i('what-the-*@?#!^!?',
                   ['wh', 'at', '-t', 'he', '-^', '2a', '@^', '3f', '#!', '^5', 
                    'e!', '^3', 'f', 'obj'],
                   'weird chars from spec example');

    def test_wtf_roundtrip(self):
        self.roundtrip('what-the-*@?#!^!?',
                   'weird chars from spec example - roundtrip');

    def test_weird(self):
        self.i2p2i('\\"*+,<=>?^|',
                   ['^5', 'c^', '22', '^2', 'a^', '2b', '^2', 'c^', '3c', '^3',
                    'd^', '3e', '^3', 'f^', '5e', '^7', 'c', 'obj'],
                   'all weird visible chars');

    def test_weird_roundtrip(self):
        self.roundtrip('\\"*+,<=>?^|',
                   'all weird visible chars - roundtrip');

    def test_basic_roundtrip(self):
        self.roundtrip('asdfghjklpoiuytrewqxcvbnm1234567890:;/', 'Basic Roundtrip')

    def test_french_roundtrip(self):
        self.roundtrip(u'Années de Pèlerinage', 'French Unicode roundtrip')

    def test_japanese_rountrip(self):
        self.roundtrip(u'ウインカリッスの日本語', 'Japanese Unicode roundtrip')
        
    def test_hardcore_unicode_rountrip(self):
        # If this works...
        self.roundtrip(u"""   1. Euro Symbol: €.
   2. Greek: Μπορώ να φάω σπασμένα γυαλιά χωρίς να πάθω τίποτα.
   3. Íslenska / Icelandic: Ég get etið gler án þess að meiða mig.
   4. Polish: Mogę jeść szkło, i mi nie szkodzi.
   5. Romanian: Pot să mănânc sticlă și ea nu mă rănește.
   6. Ukrainian: Я можу їсти шкло, й воно мені не пошкодить.
   7. Armenian: Կրնամ ապակի ուտել և ինծի անհանգիստ չըներ։
   8. Georgian: მინას ვჭამ და არა მტკივა.
   9. Hindi: मैं काँच खा सकता हूँ, मुझे उस से कोई पीडा नहीं होती.
  10. Hebrew(2): אני יכול לאכול זכוכית וזה לא מזיק לי.
  11. Yiddish(2): איך קען עסן גלאָז און עס טוט מיר נישט װײ.
  12. Arabic(2): أنا قادر على أكل الزجاج و هذا لا يؤلمني.
  13. Japanese: 私はガラスを食べられます。それは私を傷つけません。
  14. Thai: ฉันกินกระจกได้ แต่มันไม่ทำให้ฉันเจ็บ """,
                        "hardcore unicode test - roundtrip")

    def test_french(self):
        self.i2p2i('Années de Pèlerinage',
                   ['An', 'n^', 'c3', '^a', '9e', 's^', '20', 'de', '^2', '0P',
                    '^c', '3^', 'a8', 'le', 'ri', 'na', 'ge', 'obj'],
                   'UTF-8 chars')

        self.i2p2i("Années de Pèlerinage (Years of Pilgrimage) (S.160, S.161,\n\
 S.163) is a set of three suites by Franz Liszt for solo piano. Liszt's\n\
 complete musical style is evident in this masterwork, which ranges from\n\
 virtuosic fireworks to sincerely moving emotional statements. His musical\n\
 maturity can be seen evolving through his experience and travel. The\n\
 third volume is especially notable as an example of his later style: it\n\
 was composed well after the first two volumes and often displays less\n\
 showy virtuosity and more harmonic experimentation.",
                   ['An', 'n^', 'c3', '^a', '9e', 's^', '20', 'de', '^2', '0P',
                    '^c', '3^', 'a8', 'le', 'ri', 'na', 'ge', '^2', '0(', 'Ye',
                    'ar', 's^', '20', 'of', '^2', '0P', 'il', 'gr', 'im', 'ag', 
                    'e)', '^2', '0(', 'S,', '16', '0^', '2c', '^2', '0S', ',1',
                    '61', '^2', 'c^', '0a', '^2', '0S', ',1', '63', ')^', '20',
                    'is', '^2', '0a', '^2', '0s', 'et', '^2', '0o', 'f^', '20', 
                    'th', 're', 'e^', '20', 'su', 'it', 'es', '^2', '0b', 'y^', 
                    '20', 'Fr', 'an', 'z^', '20', 'Li', 'sz', 't^', '20', 'fo', 
                    'r^', '20', 'so', 'lo', '^2', '0p', 'ia', 'no', ',^', '20',
                    'Li', 'sz', 't\'', 's^', '0a', '^2', '0c', 'om', 'pl', 'et',
                    'e^', '20', 'mu', 'si', 'ca', 'l^', '20', 'st', 'yl', 'e^',
                    '20', 'is', '^2', '0e', 'vi', 'de', 'nt', '^2', '0i', 'n^',
                    '20', 'th', 'is', '^2', '0m', 'as', 'te', 'rw', 'or', 'k^',
                    '2c', '^2', '0w', 'hi', 'ch', '^2', '0r', 'an', 'ge', 's^',
                    '20', 'fr', 'om', '^0', 'a^', '20', 'vi', 'rt', 'uo', 'si',
                    'c^', '20', 'fi', 're', 'wo', 'rk', 's^', '20', 'to', '^2',
                    '0s', 'in', 'ce', 're', 'ly', '^2', '0m', 'ov', 'in', 'g^',
                    '20', 'em', 'ot', 'io', 'na', 'l^', '20', 'st', 'at', 'em',
                    'en', 'ts', ',^', '20', 'Hi', 's^', '20', 'mu', 'si', 'ca',
                    'l^', '0a', '^2', '0m', 'at', 'ur', 'it', 'y^', '20', 'ca',
                    'n^', '20', 'be', '^2', '0s', 'ee', 'n^', '20', 'ev', 'ol',
                    'vi', 'ng', '^2', '0t', 'hr', 'ou', 'gh', '^2', '0h', 'is',
                    '^2', '0e', 'xp', 'er', 'ie', 'nc', 'e^', '20', 'an', 'd^',
                    '20', 'tr', 'av', 'el', ',^', '20', 'Th', 'e^', '0a', '^2',
                    '0t', 'hi', 'rd', '^2', '0v', 'ol', 'um', 'e^', '20', 'is',
                    '^2', '0e', 'sp', 'ec', 'ia', 'll', 'y^', '20', 'no', 'ta',
                    'bl', 'e^', '20', 'as', '^2', '0a', 'n^', '20', 'ex', 'am',
                    'pl', 'e^', '20', 'of', '^2', '0h', 'is', '^2', '0l', 'at',
                    'er', '^2', '0s', 'ty', 'le', '+^', '20', 'it', '^0', 'a^',
                    '20', 'wa', 's^', '20', 'co', 'mp', 'os', 'ed', '^2', '0w',
                    'el', 'l^', '20', 'af', 'te', 'r^', '20', 'th', 'e^', '20',
                    'fi', 'rs', 't^', '20', 'tw', 'o^', '20', 'vo', 'lu', 'me',
                    's^', '20', 'an', 'd^', '20', 'of', 'te', 'n^', '20', 'di',
                    'sp', 'la', 'ys', '^2', '0l', 'es', 's^', '0a', '^2', '0s',
                    'ho', 'wy', '^2', '0v', 'ir', 'tu', 'os', 'it', 'y^', '20',
                    'an', 'd^', '20', 'mo', 're', '^2', '0h', 'ar', 'mo', 'ni',
                    'c^', '20', 'ex', 'pe', 'ri', 'me', 'nt', 'at', 'io', 'n,', 'obj'],                   
                   'very long id with apostrophes and UTF-8 chars')

    def test_id_to_url_simple(self):
        desired_url = "file://%s/pairtree_root/fo/o/obj/bar.txt" % PAIRTREE_STORAGE_DIR
        test_url = self.pairtree.get_url("foo", "bar.txt")
        self.assertEquals(desired_url, test_url)


    def test_id_to_url_withpath(self):
        desired_url = "file://%s/pairtree_root/fo/o/obj/data/subdir/bar.txt" % PAIRTREE_STORAGE_DIR
        test_url = self.pairtree.get_url("foo", "bar.txt", path="data/subdir")
        self.assertEquals(desired_url, test_url)


if __name__ == '__main__':
    unittest.main()
