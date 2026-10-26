# frozen_string_literal: true

module StringBlank
  refine String do
    def blank?
      strip.empty?
    end
  end
end
