from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from openai import AsyncAzureOpenAI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .services.globals import clients
from .api import chat
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Defines startup and shutdown logic of the FastAPI app
    # Instantiate the OpenAI client
    clients["azure_openai"] = AsyncAzureOpenAI(
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"), 
        api_key=os.getenv("AZURE_OPENAI_KEY"),  
        api_version="2023-09-01-preview"
    )
    # Instantiate the Cognitive Search client
    search_key = os.getenv("AZURE_SEARCH_KEY")
    clients["azure_search"] = SearchClient(
        endpoint = os.getenv("AZURE_SEARCH_ENPOINT"),
        index_name = os.getenv("AZURE_SEARCH_INDEX_NAME"), 
        credential = AzureKeyCredential(search_key)
    )
    yield
    await clients["azure_openai"].close()
    await clients["azure_search"].close()

def create_app():
    load_dotenv(override=True)
    is_dev = os.getenv('RUNNING_ENV') == 'dev'
    app = FastAPI(docs_url="/docs" if is_dev else None,
            redoc_url="/redoc" if is_dev else None,
            openapi_url="/openapi.json" if is_dev else None,
            lifespan=lifespan)
    
    @app.get("/")
    def get_root():
        return {"message": "FastAPI running in a Lambda function"}
    
    app.include_router(chat.router)

    if is_dev:
        origins = ["http://localhost"]
        origins.append(os.getenv('ALLOWED_ORIGINS'))
        # Generate Swagger schema
        import json
        openapi_schema = app.openapi()
        openapi_schema_json = json.dumps(openapi_schema, indent=2)
        with open('openapi_schema.json', 'w') as file:
            file.write(openapi_schema_json)
    else:
        origins = ["https://frontend-socram-testing.vercel.app/"]
        origins.append(os.getenv('ALLOWED_ORIGINS'))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app