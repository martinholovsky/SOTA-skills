package com.example;

import java.security.SecureRandom;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

final class Sealer {

    private static final SecureRandom RNG = new SecureRandom();

    static byte[] seal(SecretKey key, byte[] data) throws Exception {
        byte[] nonce = new byte[12];
        RNG.nextBytes(nonce);
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(128, nonce));
        return c.doFinal(data);
    }
}
