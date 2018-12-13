# -*- coding: utf-8 -*-
import random, unittest, re

import os

from ofs.local import ZOFS

class TestPairtreeOFS(unittest.TestCase):
   
    def setUp(self):
        self.o = ZOFS("zofs_deleteme.zip", mode="a", quiet=True)

    def tearDown(self):
        self.o.close()
        os.remove("zofs_deleteme.zip")

    def test_empty(self):
        pass
        
    def test_store_bytes_no_params(self):
        a = self.o.claim_bucket()
        label = "foo.txt"
        b = self.o.put_stream(a, label, "Some bytes to store")
        
    def test_store_bytes_and_assert_exists(self):
        a = self.o.claim_bucket()
        label = "foo.txt"
        b = self.o.put_stream(a, label, "Some bytes to store")
        self.assertTrue(self.o.exists(a,label))
        
    def test_store_bytes_and_delete(self):
        a = self.o.claim_bucket()
        label = "foo.txt"
        b = self.o.put_stream(a, label, "Some bytes to store")
        self.assertTrue(self.o.exists(a,label))
        self.o.del_stream(a, label)
        self.assertFalse(self.o.exists(a,label))
        
        
    def test_store_bytes_no_params(self):
        a = self.o.claim_bucket()
        label = "foo.txt"
        b = self.o.put_stream(a, label, "Some bytes to store")
        self.assertEquals(b['_label'], "foo.txt")
        self.assertEquals(b['_content_length'], 19)
        self.assertEquals(b['_checksum'], 'md5:eee89bbbcf416f658c7bc18cd8f2b61d')
        
    def test_store_and_retrieve(self):
        a = self.o.claim_bucket()
        label = "foo.txt"
        b = self.o.put_stream(a, label, "Some bytes to store")
        self.assertEquals(b['_label'], "foo.txt")
        self.assertEquals(b['_content_length'], 19)
        self.assertEquals(b['_checksum'], 'md5:eee89bbbcf416f658c7bc18cd8f2b61d')
        c = self.o.get_stream(a, label, as_stream=False)
        self.assertEquals(len(c), 19)
        import hashlib
        hash_gen = hashlib.md5()
        hash_gen.update(c)
        self.assertEquals("md5:%s" % hash_gen.hexdigest(),'md5:eee89bbbcf416f658c7bc18cd8f2b61d')
    
    def test_store_bytes_with_params(self):
        a = self.o.claim_bucket()
        label = "foo.txt"
        b = self.o.put_stream(a, label, "Some bytes to store", {"a":"1", "b":[1,2,3,4,5]})
        self.assertEquals(b['a'], "1")
        self.assertEquals(b['b'], [1,2,3,4,5])
        self.assertEquals(b['_label'], "foo.txt")
        self.assertEquals(b['_content_length'], 19)
        self.assertEquals(b['_checksum'], 'md5:eee89bbbcf416f658c7bc18cd8f2b61d')
        
        
    def test_store_with_params_then_retrieve(self):
        a = self.o.claim_bucket()
        label = "foo.txt"
        b = self.o.put_stream(a, label, "Some bytes to store", {"a":"1", "b":[1,2,3,4,5]})
        self.assertEquals(b['a'], "1")
        self.assertEquals(b['b'], [1,2,3,4,5])
        self.assertEquals(b['_label'], "foo.txt")
        self.assertEquals(b['_content_length'], 19)
        self.assertEquals(b['_checksum'], 'md5:eee89bbbcf416f658c7bc18cd8f2b61d')
        c = self.o.get_metadata(a, label)
        self.assertEquals(c['a'], "1")
        self.assertEquals(c['b'], [1,2,3,4,5])
        self.assertEquals(c['_label'], "foo.txt")
        self.assertEquals(c['_content_length'], 19)
        self.assertEquals(c['_checksum'], 'md5:eee89bbbcf416f658c7bc18cd8f2b61d')
        
    def test_store_params_after_bytes(self):
        a = self.o.claim_bucket()
        label = "foo.txt"
        self.o.put_stream(a, label, "Some bytes to store")
        b = self.o.update_metadata(a, label, {"a":"1", "b":[1,2,3,4,5]})
        self.assertEquals(b['a'], "1")
        self.assertEquals(b['b'], [1,2,3,4,5])
    
    def test_foo(self): pass
    
if __name__ == '__main__':
    unittest.main()
