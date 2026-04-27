import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("--- Testing GET /health ---")
health_res = requests.get(f"{BASE_URL}/health")
print(health_res.json(), "\n")

print("--- Testing GET /model/info ---")
info_res = requests.get(f"{BASE_URL}/model/info")
print(info_res.json(), "\n")

print("--- Testing POST /predict ---")
test_cases = [
    {
        "name": "Kothrud 2BHK",
        "payload": {
            "property_type": " ", "area": 1200, "sub_area": "kothrud",
            "description": "Spacious 2 BHK apartment with modular kitchen and garden view in gated community",
            "clubhouse": 1, "school": 1, "hospital": 0, "mall": 0, "park": 1, "pool": 0, "gym": 1
        }
    },
    {
        "name": "Baner 3BHK Premium",
        "payload": {
            "property_type": 3, "area": 2000, "sub_area": "baner",
            "description": "Premium 3 BHK flat offering world class amenities swimming pool gym club house",
            "clubhouse": 1, "school": 1, "hospital": 1, "mall": 1, "park": 1, "pool": 1, "gym": 1
        }
    }
]

for tc in test_cases:
    print(f"Predicting for: {tc['name']}")
    response = requests.post(f"{BASE_URL}/predict", json=tc['payload'])
    
    if response.status_code == 200:
        result = response.json()
        print(f"Predicted Price: ₹{result['predicted_price']} Lakhs")
        print(f"95% Confidence Interval: ₹{result['lower_bound']}L to ₹{result['upper_bound']}L")
        print(f"Full JSON: {json.dumps(result, indent=2)}\n")
    else:
        print(f"Error: {response.status_code} - {response.text}\n")