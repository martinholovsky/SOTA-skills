import { format } from 'date-fns';
export const label = (d: Date) => format(d, 'PP');
