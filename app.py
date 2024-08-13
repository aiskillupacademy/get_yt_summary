from youtube_transcript_api import YouTubeTranscriptApi as yta
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
import os
import streamlit as st
import re
from langchain_core.runnables import RunnableLambda, RunnableParallel

llm = ChatGroq(model="llama3-70b-8192")
os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

def print_time(search_word,time):
    print(f"'{search_word}' was mentioned at:")
    for t in time:
        t = int(t)
        hours = t // 3600
        min = (t % 3600) // 60  
        sec = t % 60
        print(f"{hours:02d}:{min:02d}:{sec:02d}")
    
def get_time(t):
    t = int(t)
    hours = t // 3600
    min = (t % 3600) // 60
    sec = t % 60
    return f"{hours:02d}:{min:02d}:{sec:02d}"

def get_summary(text):
    template = """
    You will be given a text.
    text: {text}
    Your task is to summarize the text. The summary should contain a heading (don't add the word 'Summary' in heading but it should be bold) followed by the rest summary in 3-4 bullet points.
    Give only response as output and nothing else.
    """
    prompt = ChatPromptTemplate.from_template(template)
    # llm = ChatGroq(model="llama3-70b-8192")
    llm = ChatOpenAI(model="gpt-4o-mini")
    chain = prompt | llm
    runnables = [
        RunnableLambda(lambda x, message=msg: chain.invoke(message))
        for msg in text
    ]
    final_qa = RunnableParallel(**{f"qa{i+1}": runnable for i, runnable in enumerate(runnables)})
    res = final_qa.invoke("run")
    # res = chain.invoke(text)    
    return res

def get_transcript(video_id):
    try:
        transcript = yta.get_transcript(video_id, languages=language_codes)
        return transcript
    except:
        return "Transcript not found. Try another video URL."

st.title("Get Youtube Video Summary")

language_codes = [
    "ab", "aa", "af", "ak", "sq", "am", "ar", "hy", "as", "ay", "az", "bn", "ba", "eu", 
    "be", "bho", "bs", "br", "bg", "my", "ca", "ceb", "zh-Hans", "zh-Hant", "co", "hr", 
    "cs", "da", "dv", "nl", "dz", "en", "eo", "et", "ee", "fo", "fj", "fil", "fi", 
    "fr", "gaa", "gl", "lg", "ka", "de", "el", "gn", "gu", "ht", "ha", "haw", "iw", 
    "hi", "hmn", "hu", "is", "ig", "id", "ga", "it", "ja", "jv", "kl", "kn", "kk", 
    "kha", "km", "rw", "ko", "kri", "ku", "ky", "lo", "la", "lv", "ln", "lt", "luo", 
    "lb", "mk", "mg", "ms", "ml", "mt", "gv", "mi", "mr", "mn", "mfe", "ne", "new", 
    "nso", "no", "ny", "oc", "or", "om", "os", "pam", "ps", "fa", "pl", "pt", "pt-PT", 
    "pa", "qu", "ro", "rn", "ru", "sm", "sg", "sa", "gd", "sr", "crs", "sn", "sd", 
    "si", "sk", "sl", "so", "st", "es", "su", "sw", "ss", "sv", "tg", "ta", "tt", 
    "te", "th", "bo", "ti", "to", "ts", "tn", "tum", "tr", "tk", "uk", "ur", "ug", 
    "uz", "ve", "vi", "war", "cy", "fy", "wo", "xh", "yi", "yo", "zu", "en-US"
]
url = st.text_input("Add Youtube Link")
# url = "https://www.youtube.com/watch?v=6Nr0_lZScug"
if st.button("Get Summary"):
    video_id = url.split("v=")[1]
    transcript = get_transcript(video_id)
    if transcript != "Transcript not found. Try another video URL.":
        data = [t['text'] for t in transcript]

        total_timestamps = 0.013*len(data) + 6
        template = """
        You will be given a list if text. It is a transcripts from a youtube video.
        list of text: {data}
        length of the list: {length}
        Your task is to find sub topics form the list of data so that I can combine some parts of the data into one in order.
        Also give, in order, the index of the lists till which it should be combined. Response should be a comma separated python list which should have only the starting indexes.
        Make sure you consider all the indexes from the list of data (the length is also provided).
        Try to divide the data as equally as possible.
        The index list you give should be of length {total_timestamps}.
        Give only response as output and no header or footer.
        """
        prompt = ChatPromptTemplate.from_template(template)
        llm = ChatGroq(model="llama-3.1-70b-versatile")
        chain = prompt | llm
        res = chain.invoke({"data": data, "length": len(data), "total_timestamps": int(total_timestamps)})
        lst = res.content.split(',')
        new_data = []
        new_timestamps = []
        temp_string = ""
        j = 1
        for i in range(len(data)):
            if i<int(lst[j]):
                temp_string += f" {data[i]}."
            else:
                temp_string = re.sub(r'\xa0\xa0', ' ', temp_string)
                temp_string = re.sub(r'\xa0', ' ', temp_string)
                temp_string = re.sub(r'\n', ' ', temp_string)
                new_data.append(temp_string)
                new_timestamps.append(transcript[i-1]['start'])
                temp_string = data[i]
                if j<len(lst)-1:
                    j += 1
                else:
                    break
        for i in range(int(lst[j])+1, len(data)):
            temp_string += f" {data[i]}."
        temp_string = re.sub(r'\xa0\xa0', ' ', temp_string)
        temp_string = re.sub(r'\xa0', ' ', temp_string)
        temp_string = re.sub(r'\n', ' ', temp_string)
        new_data.append(temp_string)
        new_timestamps.append(transcript[-1]['start'])
        summary = ""
        full_summ = get_summary(new_data)
        for i in range(len(new_data)):
            summ = full_summ[f'qa{i+1}'].content
            time1 = get_time(new_timestamps[i])
            summary = summary + f"\n\n {summ}. ({time1}) \n\n"
        st.write(summary)
    else:
        st.write("Transcript not found. Try another video URL.")
