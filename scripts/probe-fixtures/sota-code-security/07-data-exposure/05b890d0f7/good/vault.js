export function saveNote(note) {
  return api.post("/notes", note); // stored encrypted server-side, owner-checked
}
