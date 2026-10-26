# frozen_string_literal: true

def archive(out, dir)
  system("tar", "czf", out, "--", dir, exception: true)
end
