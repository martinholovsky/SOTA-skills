# frozen_string_literal: true

def parse(xml)
  Nokogiri::XML(xml) { |config| config.noent.dtdload }
end
