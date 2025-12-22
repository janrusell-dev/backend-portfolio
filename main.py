import os
import httpx
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

origins = [
    "https://janrusell-portfolio.vercel.app",
    "http://localhost:3000"

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"]
)

@app.get("/api/projects")
async def fetch_github_data():
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
            # FIXED: Indented the block inside the 'try'
            response = await client.post(
                "https://api.github.com/graphql",
                json={"query": gql_query}, 
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()

            repos = result.get("data", {}).get("viewer", {}).get("repositories", {}).get("nodes", [])
            return [
                {
                    "title": r["name"],
                    "year": r["createdAt"][:4],
                    "stars": r["stargazerCount"],
                    "lang": r["primaryLanguage"]["name"] if r.get("primaryLanguage") else "None",
                    "link": r["url"]
                } for r in repos
            ]
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="GitHub API Error")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))