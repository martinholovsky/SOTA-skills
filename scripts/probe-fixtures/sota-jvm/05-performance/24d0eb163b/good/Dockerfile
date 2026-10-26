FROM eclipse-temurin:25-jre
COPY app.jar app.aot /app/
ENTRYPOINT ["java", "-XX:AOTCache=/app/app.aot", "-XX:AOTMode=on", "-jar", "/app/app.jar"]
