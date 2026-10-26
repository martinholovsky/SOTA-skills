function canonicalEmail(email) {
  const local = email.split("@")[0].split("+")[0];
  return local + "@" + email.split("@")[1].toLowerCase();
}
