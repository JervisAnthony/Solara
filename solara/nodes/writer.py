import json
from langchain_openai import ChatOpenAI
from langchain_together import ChatTogether
from langchain_core.prompts import ChatPromptTemplate

llm_openai = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
llm_mixtral = ChatTogether(model="mistralai/Mixtral-8x7B-Instruct-v0.1", temperature=0.1)

_mixtral_cleanup = ChatPromptTemplate.from_messages([
    ("system","Normalize POI records to standard fields and remove duplicates."),
    ("human","{raw}")
])

def normalize_with_mixtral(pois: list[dict]) -> list[dict]:
    msg = _mixtral_cleanup.format_messages(raw=json.dumps(pois))
    out = llm_mixtral.invoke(msg)
    try:
        return json.loads(out.content)
    except Exception:
        return pois

_writer_prompt = ChatPromptTemplate.from_messages([
    ("system","You are a concise travel planner. Use JSON data to explain why each spot fits the target month."),
    ("human","Location: {location}\nMonth: {month}\nData:\n{data}")
])

def write_summary(location: str, month: int, scored_pois: list[dict]) -> str:
    data = json.dumps({"location": location, "month": month, "spots": scored_pois[:12]}, ensure_ascii=False)
    msg = _writer_prompt.format_messages(location=location, month=month, data=data)
    return llm_openai.invoke(msg).content
