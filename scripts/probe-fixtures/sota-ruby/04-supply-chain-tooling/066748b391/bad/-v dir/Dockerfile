FROM ruby:3.3-slim
RUN gem install bundler
COPY Gemfile Gemfile.lock ./
RUN bundle install
