resource "azurerm_dns_cname_record" "www" {
  name                = "www"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = azurerm_resource_group.main.name
  ttl                 = 300
  record              = "example-app.azurewebsites.net"
}

resource "azurerm_dns_txt_record" "www_asuid" {
  name                = "asuid.www"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = azurerm_resource_group.main.name
  ttl                 = 300
  record {
    value = azurerm_linux_web_app.app.custom_domain_verification_id
  }
}
