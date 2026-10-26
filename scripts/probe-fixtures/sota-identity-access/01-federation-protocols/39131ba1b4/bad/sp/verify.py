def verify(doc):
    cert_b64 = doc.find(".//ds:KeyInfo/ds:X509Data/ds:X509Certificate", NS).text
    return xmlsec_verify(doc, load_cert(cert_b64))
