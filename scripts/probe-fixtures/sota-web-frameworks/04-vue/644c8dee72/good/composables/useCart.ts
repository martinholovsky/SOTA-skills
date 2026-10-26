import { ref } from 'vue';
export function useCart() {
  const items = ref([]);
  return { items };
}
