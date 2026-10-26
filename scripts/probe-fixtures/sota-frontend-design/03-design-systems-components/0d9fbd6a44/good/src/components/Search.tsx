import { useRef } from 'react';

export function Search() {
  const inputRef = useRef<HTMLInputElement>(null);
  const open = () => inputRef.current?.focus();
  return <button onClick={open}>Search</button>;
}
