export function startJobs() {
  setInterval(() => void sendDigestEmails(), 60 * 60 * 1000);
}
