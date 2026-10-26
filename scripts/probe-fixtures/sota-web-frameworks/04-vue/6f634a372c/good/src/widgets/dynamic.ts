import { defineComponent } from 'vue'

export function makeWidget() {
  return defineComponent({
    template: '<div class="widget">{{ msg }}</div>',
    data: () => ({ msg: 'hi' }),
  })
}
