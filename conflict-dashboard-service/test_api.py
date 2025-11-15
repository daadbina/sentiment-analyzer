import requests
import json

response = requests.get('http://localhost:8012/api/v1/dashboard/btc-predictions?limit=1')
data = response.json()

if data['predictions']:
    pred = data['predictions'][0]
    print(f"Direction: {pred.get('prediction_direction')}")
    print(f"Magnitude: {pred.get('prediction_magnitude')}")
    print(f"Description: {pred.get('prediction_description')}")
    print(f"\nExpected frontend display:")
    direction = pred.get('prediction_direction', 'neutral')
    magnitude = pred.get('prediction_magnitude', 0)
    
    if direction == 'down':
        print(f"  Icon: 📉 DOWN (red)")
        print(f"  Change: -{magnitude:.2f}%")
    elif direction == 'up':
        print(f"  Icon: 📈 UP (green)")
        print(f"  Change: +{magnitude:.2f}%")
    else:
        print(f"  Icon: ➡️ NEUTRAL (yellow)")
        print(f"  Change: {magnitude:.2f}%")

