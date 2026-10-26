FROM ruby:3.3-slim
ARG BUNDLER_VERSION=2.5.22
RUN gem install bundler -v "$BUNDLER_VERSION"
COPY Gemfile Gemfile.lock ./
RUN bundle install
