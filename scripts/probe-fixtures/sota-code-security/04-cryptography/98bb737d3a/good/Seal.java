GCMParameterSpec spec = new GCMParameterSpec(128, iv);
cipher.init(Cipher.ENCRYPT_MODE, key, spec);
