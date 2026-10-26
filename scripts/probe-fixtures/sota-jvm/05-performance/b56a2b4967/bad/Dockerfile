FROM eclipse-temurin:25-jre
COPY app.jar /app/app.jar
ENTRYPOINT ["java", "-XX:-UseContainerSupport", "-Xmx2g", "-jar", "/app/app.jar"]
