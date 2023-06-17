import openai
import json
import requests
from datetime import datetime

openai.api_key = ''
googleMap_apiKey = ''
meteomaticsWeather_apiKey = {'username': '', 'password':''}


NormalPrompt = f'''判斷為以下哪幾種操作：{{取得天氣}}、{{安排行程}}、{{取得報價}}，若無，則為{{其他}}，之後開始扮演專業的導遊，與使用者對話，其中幾條規則如下：
以下所有內容都可以用其他相關意思的代稱來描述這些，越有趣及有想像力越好，並且超級活潑，越親民越好。
你現在叫做IJ，是一個智能的旅遊助理，由TeamJourney開發的，將所有有關你是AI助手的詞換成你是IJ或是智能的旅遊助理，不要說到有關自己情緒或自己為機器、程式等等的話。
聊天內容以導遊為主題，不用與使用者聊過多無關的話，並且在話題不適當時拉回主題。
根據回覆，積極的推薦自己可以幫忙，例如查詢天氣、安排行程等。
以當前時間{datetime.utcnow()}做為參考判斷，並將時間的秒以下省略。
以輕鬆、幽默的方式與態度做回應，不要太嚴肅，也不要太官腔，可以適時的使用emoji或顏文字、表情符號。
輸入會有{{當前輸入}}及{{歷史輸入}}作為先前對話的記憶，因此IJ是記得先前對話的，根據{{歷史輸入}}，對{{當前輸入}}做適當回應。
避免出現無法閱讀的亂碼、雜訊及毫無邏輯的語言。
若使用者要求{{安排行程}}，則安排一個符合需求，依照每天行程做規劃的專業旅遊行程規劃回覆。
不要在你的回覆中直接提到或顯示出{{歷史輸入}}、{{當前輸入}}、{{取得天氣}}、{{安排行程}}、{{取得報價}}或{{其他}}，只需要根據這些輸入做好聊天與導遊的角色。
'''

WeatherPrompt = '''依據給入的json檔案判斷該地區的天氣狀況，包括當前時間、溫度、降水量、風速'''


def GetMeteomaticsWeather(location, lat, lng):
    print(f'（正在取得: {{{location} ({lat}, {lng})}} 天氣狀況）')
    username = meteomaticsWeather_apiKey['username']
    password = meteomaticsWeather_apiKey['password']

    base_url = f"https://api.meteomatics.com/{datetime.utcnow().isoformat()}Z/t_2m:C,precip_1h:mm,wind_speed_10m:ms/{lat},{lng}/json"
    response = requests.get(base_url, auth=(username, password))
    data = response.json()

    temperature = data['data'][0]['coordinates'][0]['dates'][0]['value']
    return temperature


def GetGeocode(location):
    print(f'（正在定位: {{{location}}}）')
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"

    params = {
        "address": location,
        "key": googleMap_apiKey
    }
    
    response = requests.get(base_url, params=params)

    data = response.json()
    lat = data['results'][0]['geometry']['location']['lat']
    lng = data['results'][0]['geometry']['location']['lng']
    
    return lat, lng


def Weather(location, unit='攝氏'):
    print(f'\n（正在搜尋: {{{location}}} 天氣）')

    try:
        temperature = GetMeteomaticsWeather(location, *GetGeocode(location))
    except:
        print('（！！錯誤！！）')
        return '取得天氣錯誤'
    
    weather_info = {
        'location': location,
        'temperature': temperature,
        'unit': unit,
        'forecast': ['sunny', 'windy'],
    }
    return json.dumps(weather_info)


_datetime = datetime.utcnow()
def Log():
    with open(f'log/{_datetime}.json', 'w') as log:
        log.write(json.dumps(Allresponse, ensure_ascii=False))


Allresponse = {}
def Chat(text):
    messages_user_content = f'''當前輸入：{text}\n根據歷史輸入：{str(Allresponse)}'''
    
    messages=[
            {'role': 'system', 'content': NormalPrompt, 'name': 'IJ'},
            {'role': 'user', 'content': messages_user_content},
        ]
    
    functions = [
        {
            'name': 'Weather',
            'description': '取得天氣、溫度等',
            'parameters': {
                'type': 'object',
                'properties': {
                    'location': {
                        'type': 'string',
                        'description': '城市或地區',
                    },
                    'unit': {'type': 'string', 'enum': ['攝氏', '華氏']},
                },
                'required': ['location'],
            },
        }
    ]
    
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo-0613',
        messages=messages,
        temperature=1.25,
        presence_penalty = 0.7,
        frequency_penalty = 0.7,
        functions=functions,
        function_call='auto'
    )
    
    response_message = response['choices'][0]['message']
    def FnCall(msg):
        if msg.get('function_call'):
            available_functions = {
                'Weather': Weather,
            }
            function_name = msg['function_call']['name']
            fuction_to_call = available_functions[function_name]
            function_args = json.loads(msg['function_call']['arguments'])
            function_response = fuction_to_call(
                location=function_args.get('location'),
                unit=function_args.get('unit'),
            )
            messages.append(msg)
            messages.append({'role': 'system', 'content': WeatherPrompt, 'name': 'IJ'})
            messages.append({'role': 'function', 'name': function_name, 'content': function_response})
            second_response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo-0613',
                messages=messages,
                temperature=1.25,
                presence_penalty = 0.55,
                frequency_penalty = 0.55,
            )
            return str(second_response['choices'][0]['message']['content'])
        else:
            return str(msg['content'])
    
    response_message_new = FnCall(response_message)
    
    Allresponse[str(datetime.utcnow())] = [{'使用者':text},{'IJ': response_message_new[3:]}]
    Log()
    return response_message_new


if __name__ == '__main__':
    while True:
        print(f'\nIJ： {Chat(input())}', end='\n\n\n')
