# -*- coding: utf-8 -*-
import random, unittest, re

import shutil

from ofs.local import MDOFS

class TestMDOFS(unittest.TestCase):
   
    def setUp(self):
        self.o = MDOFS(storage_dir="pt_deleteme")

    def tearDown(self):
        shutil.rmtree("pt_deleteme")

    def test_empty(self):
        pass
    
    def test_claim_bucket(self):
        a = self.o.claim_bucket()
        self.assertTrue(self.o.exists(a))
    
    def test_store_bytes_no_params(self):
        a = self.o.claim_bucket()
        label = "foo.txt"
        b = self.o.put_stream(a, label, "Some bytes to store")
        self.assertEquals(b['_label'], "foo.txt")
        self.assertEquals(b['_content_length'], 19)
        self.assertEquals(b['_checksum'], 'md5:eee89bbbcf416f658c7bc18cd8f2b61d')
    
    def test_store_bytes_with_params(self):
        a = self.o.claim_bucket()
        label = "foo.txt"
        b = self.o.put_stream(a, label, "Some bytes to store", {"a":"1", "b":[1,2,3,4,5]})
        self.assertEquals(b['a'], "1")
        self.assertEquals(b['b'], [1,2,3,4,5])
        self.assertEquals(b['_label'], "foo.txt")
        self.assertEquals(b['_content_length'], 19)
        self.assertEquals(b['_checksum'], 'md5:eee89bbbcf416f658c7bc18cd8f2b61d')
    
    def test_store_params_after_bytes(self):
        a = self.o.claim_bucket()
        label = "foo.txt"
        self.o.put_stream(a, label, "Some bytes to store")
        b = self.o.update_metadata(a, label, {"a":"1", "b":[1,2,3,4,5]})
        self.assertEquals(b['a'], "1")
        self.assertEquals(b['b'], [1,2,3,4,5])
        
    def test_params_persistence(self):
        a = self.o.claim_bucket()
        label = "foo.txt"
        self.o.put_stream(a, label, "Some bytes to store", {"a":"1", "b":[1,2,3,4,5]})
        b = self.o.get_metadata(a, label)        
        self.assertEquals(b['a'], "1")
        self.assertEquals(b['b'], [1,2,3,4,5])
        
    def test_params_deletion(self):
        a = self.o.claim_bucket()
        label = "foo.txt"
        self.o.put_stream(a, label, "Some bytes to store", {"a":"1", "b":[1,2,3,4,5]})
        self.o.del_metadata_keys(a, label, ['b'])
        b = self.o.get_metadata(a, label)     
        self.assertEquals(b['a'], "1")
        self.assertFalse(b.has_key('b'))
        
if __name__ == '__main__':
    unittest.main()
