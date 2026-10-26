GCMParameterSpec spec = new GCMParameterSpec(96, iv);
cipher.init(Cipher.ENCRYPT_MODE, key, spec);
