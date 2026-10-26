FROM eclipse-temurin:25-jre
COPY app.jar app.aot /app/
ENTRYPOINT ["java", "-XX:AOTCache=/app/app.aot", "--add-opens=java.base/java.lang=ALL-UNNAMED", "-jar", "/app/app.jar"]
