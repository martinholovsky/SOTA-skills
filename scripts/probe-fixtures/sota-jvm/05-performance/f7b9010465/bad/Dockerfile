FROM ghcr.io/graalvm/native-image-community:25 AS build
COPY . /src
WORKDIR /src
RUN native-image -jar target/app.jar -o app

FROM gcr.io/distroless/base
COPY --from=build /src/app /app
ENTRYPOINT ["/app"]
