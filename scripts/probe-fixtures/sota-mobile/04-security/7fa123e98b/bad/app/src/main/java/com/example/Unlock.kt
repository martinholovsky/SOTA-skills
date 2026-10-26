val info = BiometricPrompt.PromptInfo.Builder()
    .setTitle("Approve transfer")
    .setAllowedAuthenticators(BIOMETRIC_STRONG or DEVICE_CREDENTIAL)
    .build()
