FROM eclipse-temurin:25-jre
COPY app.jar /app/app.jar
ENTRYPOINT ["java", "-XX:StartFlightRecording", "-XX:FlightRecorderOptions:redact-key=+apikey", "-jar", "/app/app.jar"]
