# frozen_string_literal: true

Settings = Data.define(:host, :port)
SETTINGS = Settings.new(host: "db", port: 5432)
