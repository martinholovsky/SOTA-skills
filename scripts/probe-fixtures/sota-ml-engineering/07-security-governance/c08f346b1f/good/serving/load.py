from model_signing import verifying
verifying.Config().use_sigstore_verifier(identity=ID, oidc_issuer=ISSUER).verify('model/', 'model.sig')
