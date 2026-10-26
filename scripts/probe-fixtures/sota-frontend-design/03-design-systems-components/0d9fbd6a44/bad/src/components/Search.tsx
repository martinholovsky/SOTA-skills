export function Search() {
  const open = () => {
    (document.querySelector('#search-dialog input') as HTMLInputElement).focus();
  };
  return <button onClick={open}>Search</button>;
}
