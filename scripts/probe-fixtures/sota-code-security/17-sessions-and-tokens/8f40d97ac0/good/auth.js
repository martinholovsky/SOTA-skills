keycloak.init({ pkceMethod: "S256" });
loginButton.addEventListener("click", () => keycloak.login());
