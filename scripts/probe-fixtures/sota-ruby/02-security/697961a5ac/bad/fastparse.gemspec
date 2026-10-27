Gem::Specification.new do |spec|
  spec.name = "fastparse"
  spec.version = "0.1.0"
  spec.files = Dir["lib/**/*.rb", "ext/**/*.{c,h,rb}"]
  spec.extensions = ["ext/fastparse/extconf.rb"]
end
