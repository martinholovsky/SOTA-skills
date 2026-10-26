export function TodoList({ todos }: { todos: Todo[] }) {
  return <ul>{todos.map((todo) => <li key={todo.id}>{todo.text}</li>)}</ul>
}
