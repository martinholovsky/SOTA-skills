# frozen_string_literal: true

def history(path)
  IO.popen("git log -- #{path}", &:read)
end
