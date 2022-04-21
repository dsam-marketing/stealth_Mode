from cgitb import text
import json
from json.tool import main
from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.natural_language_understanding_v1 import Features, EmotionOptions


ENTITIES = ["important", "urgent", "asap", "emergency", "unusual", "bug", "error", "compromised", "issue", "software", "voicemail", "quickly" ]
NEG_EMOTIONS = ["anger", "disgust", "fear", "sadness"]
POS_EMOTIONS = ["joy"]


authenticator = IAMAuthenticator('iZfTKBZOO9GLYun6JEC2x5UyRX5GaHQP3vmHSgeTX-5m')
natural_language_understanding = NaturalLanguageUnderstandingV1(
    version='2022-04-07',
    authenticator=authenticator
)
natural_language_understanding.set_service_url('https://api.eu-gb.natural-language-understanding.watson.cloud.ibm.com/instances/a8c4b690-e67e-406a-94cd-5fd94a0951ea')


def run(input_text):

    output = dict()
    # Get the NLU response on the targeted keywords
    nlu_response = natural_language_understanding.analyze(text=input_text.lower(), features=Features(emotion=EmotionOptions(targets=ENTITIES))).get_result()
    # filter on the emotion
    emotions_dict = nlu_response["emotion"]
    # filter on the keywords emotions
    targeted_words_emotion = emotions_dict["targets"]
    scores = list()
    # iterate on each keyword details in order to compute the overall scores
    for target_items in targeted_words_emotion:
        emotion_target = target_items["emotion"]   
        sorted_scores = get_sorted_scores(emotion_target)
        main_emotions = get_main_emotions(sorted_scores)
        scores.append(main_emotions)
    overall = compute_overall_emotion(scores)

    # concatenate the output json file
    output["text"] = input_text 
    output["sentiment"] = overall
    output["detailed_sentiment"] =  targeted_words_emotion 
    return output


# function that computes the overall sentiment based on the keywords sentiment
def compute_overall_emotion(scores):
    positive = 0.0
    negative = 0.0
    counter_positive = 0.0
    counter_negatif = 0.0
    for score_item in scores:
        # Iterate over all the items in dictionary and filter items which has even keys
        for (key, value) in score_item.items():
            if key in POS_EMOTIONS:
                positive += value
                counter_positive +=1.0
            elif key in NEG_EMOTIONS:
                negative += value
                counter_negatif +=1.0
    if counter_negatif > 0.0 :
        negative = negative/counter_negatif

    if counter_positive >0.0:
        positive = positive/counter_positive
    return {"positif":positive, "negatif": negative}


def get_sorted_scores(emotion_target):
    return {k: v for k, v in sorted(emotion_target.items(), key=lambda item: item[1], reverse=True)}

# function that filters on the emotions > 0.10 
def get_main_emotions(sorted_scores):
    main_emotions = dict()
    # Iterate over all the items in dictionary and filter items which has even keys
    for (key, value) in sorted_scores.items():
    # Check if key is even then add pair to new dictionary
        if value >= 0.10:
            main_emotions[key] = value
    return main_emotions




if __name__ == '__main__':
    texts = ["Hi it’s Mal. We have discussed your mortgage account. There seem to be unusual activity on your account. Please call us or visit branch", "Hi. Can you call me quickly. It’s regarding your loan instalment.", "Hi. It’s Sam from IT support. We have fixed the urgent issues you had with your voicemail. Please contact us", "Hi there, this is important, call me! "]
    for input_text in texts:
        print(json.dumps(run(input_text), indent=2))
