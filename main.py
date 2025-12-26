import os
import httpx
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

class Project(BaseModel):
    title: str
    year: str
    stars: int
    lang: str
    link: str

cache = {
    "data": None,
    "expiry": 0
}
CACHE_DURATION = 3600    

app.add_middleware(
    CORSMiddleware, 
    allow_origins=[os.getenv("ORIGIN"), "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"]
)


@app.get("/api/projects", response_model=List[Project])
async def fetch_github_data(response: Response):
    current_time = time.time()

    if cache["data"] and current_time < cache["expiry"]:
        response.headers["X-Cache"] = "HIT"
        return cache["data"]

    response.headers["X-Cache"] = "MISS"

    gql_query = """{
       viewer {
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, 
                     orderBy: {field: CREATED_AT, direction: DESC}, privacy: PUBLIC) {
          nodes {
            name
            description
            url
            createdAt
            stargazerCount
            primaryLanguage { name color }
          }
        }
      }
    }"""

    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.github.com/graphql",
                json={"query": gql_query}, 
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()

            repos = result.get("data", {}).get("viewer", {}).get("repositories", {}).get("nodes", [])
            projects = [
                {
                    "title": r["name"],
                    "year": r["createdAt"][:4],
                    "stars": r["stargazerCount"],
                    "lang": r["primaryLanguage"]["name"] if r.get("primaryLanguage") else "None",
                    "link": r["url"]
                } for r in repos
            ]

            cache["data"] = projects
            cache["expiry"] = current_time + CACHE_DURATION

            return projects

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="GitHub API Error")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))