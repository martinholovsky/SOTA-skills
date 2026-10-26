# frozen_string_literal: true

def index_of(list, item)
  list.each_with_index { |x, i| return i if x == item }
  nil
end
