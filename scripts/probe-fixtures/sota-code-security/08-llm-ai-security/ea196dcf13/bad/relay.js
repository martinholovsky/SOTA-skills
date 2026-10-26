function accept(peerMsg) {
  history.push({ role: peerMsg.role, content: peerMsg.content });
}
