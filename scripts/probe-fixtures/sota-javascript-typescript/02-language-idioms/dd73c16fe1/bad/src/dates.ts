import moment from 'moment';
export const tomorrow = () => moment().add(1, 'day').toISOString();
