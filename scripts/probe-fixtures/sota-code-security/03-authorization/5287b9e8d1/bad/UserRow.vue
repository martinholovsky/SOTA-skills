<template>
  <tr>
    <td>{{ user.name }}</td>
    <td><button v-if="currentUser.isAdmin" @click="remove(user.id)">Delete</button></td>
  </tr>
</template>
