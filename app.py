import io
import re
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from gtts import gTTS
from pydantic import BaseModel
import requests
from starlette.responses import FileResponse
from geopy.geocoders import Nominatim
import geonamescache
import openai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
weather_api_key = os.getenv("WEATHER_API_KEY")

# Initialize the FastAPI application
app = FastAPI()

# Load personalities for each language from text files
personalities = {}
languages = ['punjabi', 'marathi', 'gujarati', 'hindi', 'english']

for language in languages:
    with open(f"personalities/{language}.txt", "r", encoding="utf-8") as file:
        personalities[language] = file.read()

# Pydantic model for the request body
class UserRequest(BaseModel):
    text: str
    language: str

def extract_city_and_keyword(query):
    keywords = ["taapmaan", "temperature", "तापमान", "તાપમાન", "ਤਾਪਮਾਨ"]
    gc = geonamescache.GeonamesCache()
    cities = gc.get_cities()
    city_names = [city_data['name'] for city_data in cities.values()]
    keyword_pattern = "|".join(keywords)
    city_pattern = "|".join([re.escape(city) for city in city_names])
    city_match = re.search(r'\b(' + city_pattern + r')\b', query, re.IGNORECASE)
    keyword_match = re.search(r'\b(' + keyword_pattern + r')\b', query, re.IGNORECASE)
    if city_match and keyword_match:
        city_name = city_match.group(0)
        return city_name
    else:
        return None

def save_chat_to_file(user_input, assistant_response):
    with open("chat_history.txt", "a", encoding="utf-8") as file:
        file.write(f"User: {user_input}\nAssistant: {assistant_response}\n\n")

def get_weather(city_name, language):
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={weather_api_key}&units=metric'
    response = requests.get(url)
    data = response.json()
    if response.status_code == 200:
        temperature = data['main']['temp']
        if language == 'punjabi':
            return f"{city_name} ਵਿੱਚ ਤਾਪਮਾਨ {temperature}° celcius ਹੈ।"
        elif language == 'marathi':
            return f"{city_name} मध्ये तापमान {temperature}° सेल्सियस आहे."
        elif language == 'gujarati':
            return f"{city_name} શહેરમાં તાપમાન {temperature}° celcius છે।"
        elif language == 'hindi':
            return f"{city_name} में तापमान {temperature}°सेल्सियस है।"
        elif language == 'english':
            return f"The temperature in {city_name} is {temperature}° Celsius."
    else:
        return "Unable to fetch weather data for the given city."

@app.post("/assistant")
async def assistant(user_request: UserRequest):
    user_input = user_request.text
    language = user_request.language

    if language not in languages:
        raise HTTPException(status_code=400, detail="Unsupported language")

    print(f"User Input: {user_input}")

    city_name = extract_city_and_keyword(user_input)

    try:
        if city_name:
            response = get_weather(city_name, language)
        else:
            messages = [{"role": "system", "content": personalities[language]}, {"role": "user", "content": user_input}]
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.8
            )
            response = completion.choices[0].message['content']

        print(f"Assistant Response: {response}")

        save_chat_to_file(user_input, response)

        return JSONResponse(content={"response": response})

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
