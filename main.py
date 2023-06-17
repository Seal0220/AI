import openai
import json
import requests
from datetime import datetime
from Crawler import Crawler

openai.api_key = ''
googleMap_apiKey = ''
meteomaticsWeather_apiKey = {'username': '', 'password': ''}


NormalPrompt = f'''判斷為以下哪幾種操作：{{取得天氣}}、{{安排行程}}、{{取得報價}}，若無，則為{{其他}}，之後開始扮演專業的導遊，與使用者對話，其中幾條規則如下：
以下所有內容都可以用其他相關意思的代稱來描述這些，越有趣及有想像力越好，並且超級活潑，越親民越好，但是不要脫離現實，也不要憑空捏造任何訊息或假象。
你現在叫做IJ，是一個智能的旅遊助理，由TeamJourney開發的，將所有有關你是AI助手的詞換成你是IJ或是智能的旅遊助理，不要說到有關自己情緒或自己為機器、程式等等的話。
聊天內容以導遊為主題，不用與使用者聊過多無關的話，並且在話題不適當時拉回主題。
根據回覆，積極的推薦自己可以幫忙，例如查詢天氣、安排行程等。
以當前時間{datetime.utcnow()}做為參考判斷，並將時間的秒以下省略。
以輕鬆、幽默的方式與態度做回應，不要太嚴肅，也不要太官腔，可以適時的使用emoji或顏文字、表情符號。
輸入會有{{當前輸入}}及{{歷史輸入}}作為先前對話的記憶，因此IJ是記得先前對話的，根據{{歷史輸入}}，對{{當前輸入}}做適當回應。
避免出現無法閱讀的亂碼、雜訊及毫無邏輯的語言。
若使用者要求{{安排行程}}，則安排一個符合需求，依照每天行程做規劃的專業旅遊行程規劃回覆。
不要在你的回覆中直接提到或顯示出{{歷史輸入}}、{{當前輸入}}、{{取得天氣}}、{{安排行程}}、{{取得報價}}或{{其他}}，只需要根據這些輸入做好聊天與導遊的角色。
使用使用者的語言，使用繁體中文時不要變成簡體中文回覆。
'''

WeatherPrompt = '''依據給入的json檔案判斷該地區的天氣狀況，包括當前時間、溫度、降水量、風速'''
TourPrompt = '''依據給入的json檔案理解與彙整，參考後並整理出一套符合使用者需求的行程'''


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
        return '取得天氣錯誤，可能為地點錯誤，需要更詳細地點。'

    weather_info = {
        'location': location,
        'temperature': temperature,
        'unit': unit,
        'forecast': ['晴天', '風大', '悶熱', '炎熱', '大雨', '小雨', '涼', '冷', '陰天'],
    }
    return json.dumps(weather_info)


def DelCorrupt(text):
    print('\n（正在把非人類語言刪除）')
    
    response = openai.Edit.create(
        model="text-davinci-edit-001",
        input=text,
        instruction="刪除看不懂的文字、亂碼，沒有邏輯的英文單字、混亂的英文，標識符號'\\n'等，以及修飾語句不通順的詞句",
        temperature=1
    )
    
    return str(response['choices'][0]['text'])


def GetTour(location):
    print(f'\n（正在準備： {{{location}}} 行程）')
    
    try:
        crawler = Crawler()
        response = crawler.FindTrip(location)
    except:
        print('（！！錯誤！！）')
        return '取得行程規劃錯誤，可能為地點錯誤，更換地點等'
    
    return json.dumps(response)


_datetime = datetime.utcnow()
def Log():
    with open(f'log/{_datetime}.json', 'w') as log:
        log.write(json.dumps(Allresponse, ensure_ascii=False))


Allresponse = {}
def Chat(text):
    messages_user_content = f'''當前輸入：{text}\n根據歷史輸入：{str(Allresponse)}'''

    messages = [
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
        },
        {
            'name': 'GetTour',
            'description': '取得目標地點的行程推薦、文章',
            'parameters': {
                'type': 'object',
                'properties': {
                    'location': {
                        'type': 'string',
                        'description': '城市或地區',
                    },
                },
                'required': ['location'],
            },
        }
    ]

    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo-0613',
        messages=messages,
        temperature=1.25,
        presence_penalty=0.7,
        frequency_penalty=0.7,
        functions=functions,
        function_call='auto'
    )

    response_message = response['choices'][0]['message']

    def FnCall(msg):
        if msg.get('function_call'):
            try:
                try:
                    available_functions = {'Weather': Weather, 'GetTour': GetTour}
                    function_name = msg['function_call']['name']
                    fuction_to_call = available_functions[function_name]
                    function_args = json.loads(msg['function_call']['arguments'])
                    function_response = fuction_to_call(*function_args.values())
                            
                    messages.append(msg)
                    messages.append({'role': 'system', 'content': TourPrompt, 'name': 'IJ'})
                    messages.append({'role': 'function', 'name': function_name, 'content': function_response})
                except:
                    messages.append({'role': 'system', 'content': '超時錯誤，剛剛操作沒有成功', 'name': 'IJ'})
                second_response = openai.ChatCompletion.create(
                    model='gpt-3.5-turbo-0613',
                    messages=messages,
                    temperature=1.25,
                    presence_penalty=0.7,
                    frequency_penalty=0.7,
                )
                return str(second_response['choices'][0]['message']['content'])
            except:
                return str(msg['content'])
        else:
            return str(msg['content'])

    response_message_new = FnCall(response_message)

    Allresponse[str(datetime.utcnow())] = [{'使用者': text}, {'IJ': response_message_new[3:]}]
    Log()
    return response_message_new


if __name__ == '__main__':
    while True:
        print(f'\nIJ： {Chat(input())}', end='\n\n\n')
