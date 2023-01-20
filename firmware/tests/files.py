import json

example_json = {
    "name": "John",
    "age": 30,
    "city": "New York"
}

with open('test.json', 'w') as f:
    json.dump(example_json, f)

with open('test.json', 'r') as f:
    data = json.load(f)
    print(data)
