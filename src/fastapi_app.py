from chainlit.utils import mount_chainlit
from fastapi import FastAPI

from whatsapp_response import whatsapp_router

# Create FastAPI app
app = FastAPI()

# Include the WhatsApp webhook endpoint
app.include_router(whatsapp_router)

# Mount Chainlit app
mount_chainlit(app=app, target="chainlit_app.py", path="/chat")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8000, reload=True)
