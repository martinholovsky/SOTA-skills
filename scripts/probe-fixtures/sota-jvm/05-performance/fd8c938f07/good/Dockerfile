FROM eclipse-temurin:25-jre
COPY app.jar /app/app.jar
ENTRYPOINT ["java", "-XX:+UseZGC", "-jar", "/app/app.jar"]
