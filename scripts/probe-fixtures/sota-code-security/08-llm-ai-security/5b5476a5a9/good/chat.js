let buffer = "";
for await (const chunk of stream) {
  buffer += chunk;
  output.innerHTML = DOMPurify.sanitize(marked.parse(buffer));
}
