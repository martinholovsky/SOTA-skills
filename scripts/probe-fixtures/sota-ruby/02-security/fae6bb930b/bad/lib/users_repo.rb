# frozen_string_literal: true

def find(conn, id)
  conn.exec("SELECT * FROM users WHERE id = #{id}")
end
