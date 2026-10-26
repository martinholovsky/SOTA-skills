# frozen_string_literal: true

def show
  render template: "pages/show", locals: { page: @page }
end
