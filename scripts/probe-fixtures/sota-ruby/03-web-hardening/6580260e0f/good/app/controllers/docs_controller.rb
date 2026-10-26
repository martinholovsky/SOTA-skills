# frozen_string_literal: true

def show
  render template: "docs/show", locals: { page: Doc.find(params[:id]) }
end
