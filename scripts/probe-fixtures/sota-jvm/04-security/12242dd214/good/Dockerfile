FROM eclipse-temurin:25-jre
COPY app.jar /app/app.jar
ENTRYPOINT ["java", "-Djdk.tls.namedGroups=X25519MLKEM768,x25519,secp256r1", "-jar", "/app/app.jar"]
