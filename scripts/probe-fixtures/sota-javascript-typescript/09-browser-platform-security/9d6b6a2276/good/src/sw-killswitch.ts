export async function killServiceWorker() {
  for (const registration of await navigator.serviceWorker.getRegistrations()) await registration.unregister();
}
