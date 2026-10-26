export default defineEventHandler(async () => {
  return await $fetch('https://api.example.com/v1/rates')
})
