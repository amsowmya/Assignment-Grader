import requests 


url = "https://www.googleapis.com/customsearch/v1"
params = {
    "key": "AIzaSyAwzN6x5-EUM1LfrABgmpefD9MPq0KEqvs",
    "cx": "9069aca5f4a4447ae",
    "q": "Model Context Protocol MCP"
}

response = requests.get(url, params=params)
print(response.json())