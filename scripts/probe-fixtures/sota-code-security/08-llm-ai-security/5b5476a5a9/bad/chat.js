for await (const chunk of stream) {
  output.innerHTML += chunk;
}
