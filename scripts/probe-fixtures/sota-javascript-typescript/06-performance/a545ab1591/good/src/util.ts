import { debounce } from 'lodash-es';
export const save = debounce(persist, 500);
