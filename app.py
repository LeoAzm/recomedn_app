import pandas as pd
from fastapi import FastAPI, HTTPException, Depends
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List
from datetime import datetime
from pydantic import BaseModel
from catboost import CatBoostClassifier
import catboost
import os
from  sqlalchemy.orm import sessionmaker
from  sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

app = FastAPI()


connection = "postgresql://robot-startml-ro:pheiph0hahj1Vaif@"\
             "postgres.lab.karpov.courses:6432/startml"



class PostResponse(BaseModel):
    id: int
    text: str
    topic: str



def get_model_path(path: str) -> str:
    if os.environ.get("IS_LMS") == "1":  # проверяем где выполняется код в лмс, или локально. Немного магии
        MODEL_PATH = '/workdir/user_input/model'
    else:
        MODEL_PATH = path
    return MODEL_PATH


def load_models() -> catboost.core.CatBoostClassifier:
    model_path = get_model_path("/Users/leoazmanov/Desktop/leos_model-2")
    empty_model = CatBoostClassifier()
    return_model = empty_model.load_model(model_path)
    return return_model
    # LOAD MODEL HERE PLS :)

def get_db():
    with psycopg2.connect(
            dbname="startml",
            host="postgres.lab.karpov.courses",
            user="robot-startml-ro",
            password="pheiph0hahj1Vaif",
            port=6432,
            cursor_factory=RealDictCursor,
    ) as conn:
        return conn.cursor()


model = load_models()

user = pd.read_sql("""SELECT *
                        FROM "l-azmanov-9_user" """,con=connection)

post = pd.read_sql("""SELECT * FROM "l-azmanov-9_post" """,con=connection)

post["_tempkey"] = 1
user["_tempkey"] = 1


@app.get("/post/recommendations/", response_model=List[PostResponse])
def recommended_posts(
        id: int,
        time: datetime = datetime.now(),
        limit: int = 10, cur=Depends(get_db)) -> List[PostResponse]:

    data = user[user["user_id"]==id].merge(post,on = "_tempkey").drop("_tempkey",axis=1)
    data.drop(columns=["user_id"],inplace=True)


    data['probabilities'] = model.predict_proba(data)[:,1]

    post_ids = tuple(list(data.sort_values(by="probabilities",ascending=False).head(5).index))

    cur.execute(f"""SELECT post_id as id , text , topic 
                    FROM post_text_df
                    WHERE post_id in  {post_ids}""")


    return cur.fetchall()