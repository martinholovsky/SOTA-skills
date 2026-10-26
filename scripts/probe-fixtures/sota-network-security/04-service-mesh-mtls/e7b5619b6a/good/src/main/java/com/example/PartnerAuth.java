class PartnerAuth {
  boolean allowed(X509Certificate c) throws Exception {
    return PINNED_SPKI.equals(sha256(c.getPublicKey().getEncoded()))
        && sanUris(c).contains("spiffe://partner.example/api");
  }
}
