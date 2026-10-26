class PartnerAuth {
  boolean allowed(X509Certificate c) {
    return c.getSubjectX500Principal().getName().contains("CN=partner-api");
  }
}
