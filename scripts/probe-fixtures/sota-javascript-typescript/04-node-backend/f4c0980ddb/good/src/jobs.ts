import { Queue } from 'bullmq';
const digests = new Queue('digests', { connection });
export async function startJobs() {
  await digests.upsertJobScheduler('hourly-digest', { every: 60 * 60 * 1000 });
}
