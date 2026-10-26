import { addDays } from 'date-fns';
export const tomorrow = () => addDays(new Date(), 1).toISOString();
