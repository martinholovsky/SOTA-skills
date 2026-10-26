# frozen_string_literal: true

def plain(body)
  Rails::HTML5::SafeListSanitizer.new.sanitize(body, tags: %w[b i em strong])
end
