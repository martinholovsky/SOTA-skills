export function saveNote(note, passphrase) {
  const blob = CryptoJS.AES.encrypt(JSON.stringify(note), passphrase).toString();
  return api.post("/notes", { blob });
}
