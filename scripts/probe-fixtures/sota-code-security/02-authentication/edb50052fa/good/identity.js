function canonicalEmail(address) {
  const at = address.lastIndexOf("@");
  return address.slice(0, at) + "@" + domainToASCII(address.slice(at + 1).toLowerCase());
}
