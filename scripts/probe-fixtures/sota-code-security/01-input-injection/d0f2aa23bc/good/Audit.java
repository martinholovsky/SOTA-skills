String body = mapper.writeValueAsString(Map.of("user", name, "action", "login"));
client.post("/audit", body);
