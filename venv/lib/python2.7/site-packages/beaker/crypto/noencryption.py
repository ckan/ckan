"""Encryption module that does nothing"""

def aesEncrypt(data, key):
    return data

def aesDecrypt(data, key):
    return data

has_aes = False

def getKeyLength():
    return 32
