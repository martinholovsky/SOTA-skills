package com.example;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

final class Sealer {

    static byte[] seal(SecretKey key, byte[] data) throws Exception {
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(128, new byte[12]));
        return c.doFinal(data);
    }
}
