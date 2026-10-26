Cipher c = Cipher.getInstance("RSA/ECB/PKCS1Padding");
c.init(Cipher.ENCRYPT_MODE, publicKey);
