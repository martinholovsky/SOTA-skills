FROM eclipse-temurin:25-jre
COPY app.jar /app/app.jar
ENTRYPOINT ["java", "--illegal-native-access=deny", "--sun-misc-unsafe-memory-access=deny", "-jar", "/app/app.jar"]
