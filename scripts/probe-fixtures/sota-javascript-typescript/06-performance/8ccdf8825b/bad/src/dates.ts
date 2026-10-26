import * as dateFns from 'date-fns';
export const label = (d: Date) => dateFns.format(d, 'PP');
