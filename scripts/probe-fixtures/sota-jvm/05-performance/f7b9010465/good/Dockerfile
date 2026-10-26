FROM eclipse-temurin:25-jre
COPY app.jar /app/app.jar
ENTRYPOINT ["java", "-XX:+UseG1GC", "-jar", "/app/app.jar"]
