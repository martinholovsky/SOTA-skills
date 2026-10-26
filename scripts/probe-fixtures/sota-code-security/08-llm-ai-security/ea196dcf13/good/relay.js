function accept(peerMsg) {
  history.push({ role: "user", content: peerMsg.content }); // peers never set the role
}
