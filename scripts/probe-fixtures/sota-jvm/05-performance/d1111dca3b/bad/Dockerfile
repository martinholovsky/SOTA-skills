FROM eclipse-temurin:25-jre
COPY app.jar /app/app.jar
ENTRYPOINT ["java", "-XX:StartFlightRecording=filename=/shared/rec.jfr", "-Dcom.sun.management.jmxremote.port=9010", "-Dcom.sun.management.jmxremote.authenticate=false", "-jar", "/app/app.jar"]
