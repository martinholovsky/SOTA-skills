import FingerprintJS from '@fingerprintjs/fingerprintjs';

export async function visitorId() {
  const fp = await FingerprintJS.load();
  return (await fp.get()).visitorId;
}
