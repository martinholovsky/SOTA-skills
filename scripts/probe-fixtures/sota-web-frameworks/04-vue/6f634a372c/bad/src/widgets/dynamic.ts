import { defineComponent } from 'vue'

export function makeWidget(props: { template: string }) {
  return defineComponent({
    template: props.template,
  })
}
