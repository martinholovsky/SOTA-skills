# frozen_string_literal: true

EXPORTERS = { "csv" => CsvExporter, "json" => JsonExporter }.freeze

def create
  exporter = EXPORTERS.fetch(params[:type]).new
end
