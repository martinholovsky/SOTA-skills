public boolean bind(String username, String password) throws NamingException {
    String dn = "uid=" + Rdn.escapeValue(username) + ",ou=people,dc=example,dc=com";
    return directory.bind(dn, password);
}
