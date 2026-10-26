export function TodoList({ todos }: { todos: Todo[] }) {
  return <ul>{todos.map((todo, index) => <li key={index}>{todo.text}</li>)}</ul>
}
