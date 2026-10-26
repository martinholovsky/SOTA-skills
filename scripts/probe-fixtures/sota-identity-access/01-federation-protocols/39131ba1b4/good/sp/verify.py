def verify(doc, idp):
    cert = idp.metadata.signing_certificate  # pinned from IdP metadata
    return xmlsec_verify(doc, cert)
