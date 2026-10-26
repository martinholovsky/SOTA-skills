import { ref } from 'vue';
export const items = ref([]);
export function useCart() {
  return { items };
}
