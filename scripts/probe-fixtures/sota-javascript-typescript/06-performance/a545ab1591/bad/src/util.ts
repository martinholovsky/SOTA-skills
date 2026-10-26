import { debounce } from 'lodash';
export const save = debounce(persist, 500);
