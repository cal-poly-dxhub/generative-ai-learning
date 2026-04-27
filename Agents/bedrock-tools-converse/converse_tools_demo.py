import boto3
import json
import requests
from datetime import datetime

client = boto3.client("bedrock-runtime", region_name="us-west-2")
model_id = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


# --- Tool implementations ---

def get_today_date_tool():
    print("\n--- TOOL CALL: get_today_date ---")
    res = {"today": datetime.today().strftime("%Y-%m-%d")}
    print(f"Tool Result: {res}")
    print("---")
    return res


def calculator_tool(inputs):
    print("\n--- TOOL CALL: calculator ---")
    expression = inputs.get("expression", "")
    print(f"Expression: {expression}")
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        res = {"result": result}
    except Exception as e:
        res = {"error": str(e)}
    print(f"Tool Result: {res}")
    print("---")
    return res


WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


def get_weather_tool(inputs):
    print("\n--- TOOL CALL: get_weather ---")
    city = inputs.get("city", "")
    print(f"City: {city}")

    # Geocode the city name to lat/lon using Open-Meteo
    geo_resp = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={
        "name": city, "count": 1
    })
    geo_data = geo_resp.json()

    if not geo_data.get("results"):
        res = {"error": f"Could not find location: {city}"}
        print(f"Tool Result: {res}")
        print("---")
        return res

    location = geo_data["results"][0]
    lat, lon = location["latitude"], location["longitude"]
    resolved_name = location.get("name", city)

    # Fetch current weather from Open-Meteo (no API key needed)
    weather_resp = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
    })
    weather_data = weather_resp.json()["current"]

    weather_code = weather_data.get("weather_code", -1)
    res = {
        "city": resolved_name,
        "temp_f": weather_data["temperature_2m"],
        "condition": WEATHER_CODES.get(weather_code, "Unknown"),
        "humidity": weather_data["relative_humidity_2m"],
        "wind_mph": weather_data["wind_speed_10m"],
    }
    print(f"Tool Result: {res}")
    print("---")
    return res


# --- Tool specs for Bedrock ---

datetime_tool_spec = {
    "name": "get_today_date",
    "description": "Returns today's date in YYYY-MM-DD format. Use this to know the current date.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

calculator_tool_spec = {
    "name": "calculator",
    "description": "Evaluates a math expression and returns the result. Use this for any arithmetic or calculations.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A math expression to evaluate, e.g. '2 + 2' or '100 * 1.15'"
                }
            },
            "required": ["expression"]
        }
    }
}

weather_tool_spec = {
    "name": "get_weather",
    "description": "Gets the current weather for a given city. Returns temperature, conditions, and humidity.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name to get weather for"
                }
            },
            "required": ["city"]
        }
    }
}

tool_config = {
    "tools": [
        {"toolSpec": datetime_tool_spec},
        {"toolSpec": calculator_tool_spec},
        {"toolSpec": weather_tool_spec},
    ],
    "toolChoice": {"auto": {}}
}


# --- Tool routing ---

def run_tool(name, inputs):
    if name == "get_today_date":
        return get_today_date_tool()
    elif name == "calculator":
        return calculator_tool(inputs)
    elif name == "get_weather":
        return get_weather_tool(inputs)
    raise ValueError(f"Unknown tool: {name}")


# --- Converse loop ---

def ask_bedrock(prompt):
    messages = [
        {
            "role": "user",
            "content": [{"text": prompt}]
        }
    ]

    print(f"\nUser: {prompt}")
    print("Sending to Bedrock...")

    while True:
        res = client.converse(
            modelId=model_id,
            messages=messages,
            toolConfig=tool_config
        )

        output_msg = res["output"]["message"]
        messages.append(output_msg)

        # Check if the model wants to use tools
        tool_uses = [b["toolUse"] for b in output_msg["content"] if "toolUse" in b]

        if tool_uses:
            tool_results = []
            for tool_use in tool_uses:
                print(f"\nModel requested tool: {tool_use['name']}")
                print(f"Tool input: {json.dumps(tool_use['input'], indent=2)}")

                result_data = run_tool(tool_use["name"], tool_use["input"])

                tool_results.append({
                    "toolResult": {
                        "toolUseId": tool_use["toolUseId"],
                        "content": [{"json": result_data}],
                        "status": "success"
                    }
                })

            messages.append({"role": "user", "content": tool_results})
            print("\nSending tool results back to model...")
            continue

        # No tool use — extract final text response
        final_text = next(
            (b["text"] for b in output_msg["content"] if "text" in b), "")
        return final_text


if __name__ == "__main__":
    # What is the weather in San Luis Obispo in celsius
    prompt = input("Ask the model: ")
    answer = ask_bedrock(prompt)
    print(f"\nFinal Answer:\n{answer}")
