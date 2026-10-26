<template>
  <tr>
    <td>{{ user.name }}</td>
    <td><button v-if="user.allowedActions.includes('delete')" @click="remove(user.id)">Delete</button></td>
  </tr>
</template>
