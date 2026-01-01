import pandas as pd
from ydata_profiling import ProfileReport
import json

df = pd.DataFrame({
    "A": [1, 2, 3, 4, 5, 1],
    "B": [5, 4, 3, 2, 1, 5],
    "C": ["a", "b", "c", "a", "b", "c"]
})

profile = ProfileReport(df, title="Debug")
json_data = profile.to_json()
data = json.loads(json_data)

print(f"Keys: {list(data.keys())}")
print(f"Alerts type: {type(data.get('alerts', []))}")
if data.get('alerts'):
    print(f"First alert: {data['alerts'][0]}")

print(f"Variables keys: {list(data['variables'].keys())}")
print(f"Variable A keys: {list(data['variables']['A'].keys())}")
if 'correlations' in data:
    print(f"Correlations keys: {list(data['correlations'].keys())}")
