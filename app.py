from flask import Flask, request, jsonify
from pymongo import MongoClient
from config import OPENAI_API_KEY, MONGO_URI, MONGO_DB, MONGO_COLLECTION
from bson.objectid import ObjectId
from openai import OpenAI

app = Flask(__name__)

openai_client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENAI_API_KEY,
)

llm_models = ["google/gemini-2.0-flash-exp:free", "google/gemini-2.0-flash-lite-preview-02-05:free"]

mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB]
mongo_collection = mongo_db[MONGO_COLLECTION]


def get_character_by_id(character_id):
    character = mongo_collection.find_one({"_id": ObjectId(character_id)})
    if character:
        character.pop("_id")
    return character


def get_default_battle_description():
    return """
    В сумраке древней арены, освещенной тусклым светом факелов, два противника сталкиваются в жестокой битве. Оба вооружены — один с мечом, другой с молотом, их оружие сверкает в свете пламени, как светящиеся молнии. Звуки металлического удара эхом отдаются в воздухе, когда они сражаются на жизнь и смерть.

    Первый противник, ловкий и быстрый, стремится к своему врагу, выискивая слабые места в его защите. Он делает резкий выпад, и его меч пронзает воздух, пытаясь попасть в уязвимое место. Но второй персонаж, обладая огромной силой и выносливостью, парирует удар своим молотом, и даже незначительный сбой в атаке заставляет первого отступить, понимая, что его враг не так прост.

    В следующие несколько секунд они обменяются несколькими ударами. Взгляд их полон решимости, каждый из них готов дойти до конца. Однако, в один момент первый противник ослабляет бдительность, пытаясь увернуться от следующего удара молота, и этот момент становится решающим.

    Молниеносный удар молотом ломает защиту первого и он падает на колени. С последним вздохом он пытается подняться, но ослабленные силы не позволяют это сделать. Взгляд его наполнен болью и растерянностью.

    Победитель, стоя на ногах, поднимает молот в победном жесте, несмотря на усталость и повреждения, полученные в бою. Он знает, что это было не просто сражение — это было испытание его выносливости и решимости. Но победа не приходит без жертв.

    Тишина воцаряется на арене. В воздухе ощущается напряжение. Бой завершен, но внутри каждого из участников остается след этого сражения.
    """


def create_dnd_battle_prompt(json1, json2):
    prompt = f"""
    Придумай мне описание для сражения в DnD.
    Я пришлю тебе описание 2 персонажей:
    1) {json1}
    2) {json2}
    Опиши:
    - Как первый персонаж атакует второго, попадает по нему. Расскажи про сам удар и его эффект.
    - Как первый персонаж добивает второго, когда его ХП падают до нуля. 
    Оформи результат в виде текста с абзацами.  
    В выводе должно быть ТОЛЬКО описание без всяких вводных слов.
    """
    return prompt.strip()


def get_dnd_battle_description(json1, json2):
    prompt = create_dnd_battle_prompt(json1, json2)

    for model in llm_models:
        try:
            completion = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": [{"type": "text", "text": prompt}]}
                ]
            )

            return completion.choices[0].message.content

        except Exception as e:
            print(f"Ошибка при запросе к модели {model}: {e}")
            continue

    return get_default_battle_description()


@app.route('/generate_battle', methods=['POST'])
def generate_battle():
    try:
        data = request.get_json()
        first_char_id = data.get('first_char_id')
        second_char_id = data.get('second_char_id')

        if not first_char_id or not second_char_id:
            return jsonify({"error": "Необходимо указать два ID персонажей"}), 400

        first_character = get_character_by_id(first_char_id)
        second_character = get_character_by_id(second_char_id)

        if not first_character or not second_character:
            return jsonify({"error": "Один или оба персонажа не найдены"}), 404

        battle_description = get_dnd_battle_description(first_character, second_character)
        return jsonify({"battle_description": battle_description}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)