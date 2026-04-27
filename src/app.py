from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.schemas import PropertyInput, PriceResponse, HealthResponse, ModelInfoResponse
from src.inference import predict_price, get_model_info
from fastapi.staticfiles import StaticFiles # <-- NEW IMPORT

app = FastAPI(
    title="Property Price Prediction API",
    description="Inference pipeline for estimating property prices with confidence intervals.",
    version="1.0.0"
)

# ADD THIS BLOCK TO ALLOW FRONTEND REQUESTS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (for local testing)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Check if the API is up and running."""
    return HealthResponse(status="API is healthy and running.")

@app.get("/model/info", response_model=ModelInfoResponse)
def model_info():
    """Retrieve information about the loaded model artifacts."""
    info = get_model_info()
    return ModelInfoResponse(**info)

@app.post("/predict", response_model=PriceResponse)
def predict(data: PropertyInput):
    """
    Predict property price.
    Accepts raw property attributes and returns a prediction along with a 95% confidence interval.
    """
    result = predict_price(data)
    return PriceResponse(**result)


# This mounts the "frontend" directory to the root path "/".
# html=True tells FastAPI to automatically serve "index.html" when someone visits "/"
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")