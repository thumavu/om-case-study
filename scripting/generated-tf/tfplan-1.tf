resource "azurerm_data_factory" "main" {
  github_configuration = []
  global_parameter = []
  identity = [
    {
      type = "SystemAssigned"
    },
  ]
  location = "northeurope"
  managed_virtual_network_enabled = false
  name = "df-advanced-analytics-and-ai-dev-eun"
  public_network_enabled = true
  resource_group_name = "rg-data-dev-eun"
  tags = {
    AppId = "OM000000"
    CostCentre = "10020842"
    Environment = "dev"
    GitCommitHash = "55677f260132aaa75973b8f64a41f1c16a1dc201"
    GitRepoFolder = "ws-default/dev/data-factory/"
    GitRepoURL = "https://dev.azure.com/OMEngineering/IAC-Platform/_git/tf-ws-azure-advanced-analytics-and-ai"
  }
  vsts_configuration = []
}
