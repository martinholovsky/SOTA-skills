export default defineEventHandler(async (event) => {
  return await $fetch(getQuery(event).url as string)
})
