"""Encryption module that uses nsscrypto"""
import nss.nss

nss.nss.nss_init_nodb()

# Apparently the rest of beaker doesn't care about the particluar cipher,
# mode and padding used.
# NOTE: A constant IV!!! This is only secure if the KEY is never reused!!!
_mech = nss.nss.CKM_AES_CBC_PAD
_iv = '\0' * nss.nss.get_iv_length(_mech)

def aesEncrypt(data, key):
    slot = nss.nss.get_best_slot(_mech)

    key_obj = nss.nss.import_sym_key(slot, _mech, nss.nss.PK11_OriginGenerated,
                                     nss.nss.CKA_ENCRYPT, nss.nss.SecItem(key))

    param = nss.nss.param_from_iv(_mech, nss.nss.SecItem(_iv))
    ctx = nss.nss.create_context_by_sym_key(_mech, nss.nss.CKA_ENCRYPT, key_obj,
                                            param)
    l1 = ctx.cipher_op(data)
    # Yes, DIGEST.  This needs fixing in NSS, but apparently nobody (including
    # me :( ) cares enough.
    l2 = ctx.digest_final()

    return l1 + l2

def aesDecrypt(data, key):
    slot = nss.nss.get_best_slot(_mech)

    key_obj = nss.nss.import_sym_key(slot, _mech, nss.nss.PK11_OriginGenerated,
                                     nss.nss.CKA_DECRYPT, nss.nss.SecItem(key))

    param = nss.nss.param_from_iv(_mech, nss.nss.SecItem(_iv))
    ctx = nss.nss.create_context_by_sym_key(_mech, nss.nss.CKA_DECRYPT, key_obj,
                                            param)
    l1 = ctx.cipher_op(data)
    # Yes, DIGEST.  This needs fixing in NSS, but apparently nobody (including
    # me :( ) cares enough.
    l2 = ctx.digest_final()

    return l1 + l2

has_aes = True

def getKeyLength():
    return 32
