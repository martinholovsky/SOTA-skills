import { h } from 'vue'

export function renderCmsBlock(text: string) {
  return () => h('p', { class: 'cms' }, text)
}
