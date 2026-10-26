import { compile } from 'vue'

export function renderCmsBlock(userTemplate: string) {
  return compile(userTemplate)
}
