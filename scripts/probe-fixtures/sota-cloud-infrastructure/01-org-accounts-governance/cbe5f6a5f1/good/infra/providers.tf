provider "aws" {
  region = "eu-west-1"
  default_tags {
    tags = {
      owner      = "payments"
      managed-by = "terraform"
    }
  }
}
