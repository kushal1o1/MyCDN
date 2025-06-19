import requests

# CDN Configuration
CDN_URL = "http://localhost:8000"
API_KEY = "your-secret-key-here"
ORIGIN = "https://my-portfolio.com"

def test_cdn():
    try:
        # Step 1: Authenticate to get session token
        auth_response = requests.post(
            f"{CDN_URL}/auth",
            headers={
                "x-api-key": API_KEY,
                "Origin": ORIGIN
            }
        )
        
        if auth_response.status_code != 200:
            print(f"Authentication failed: {auth_response.status_code}")
            print(auth_response.text)
            return
        
        session_token = auth_response.json()["session_token"]
        print(f"Successfully authenticated. Session token: {session_token}")
        
        # Step 2: Try to fetch an image
        image_response = requests.get(
            f"{CDN_URL}/cdn/defaultpp.png",
            headers={
                "x-session-token": session_token,
                "Origin": ORIGIN
            }
        )
        
        if image_response.status_code == 200:
            print("Successfully fetched image!")
            # Save the image to verify
            with open("test_image.jpg", "wb") as f:
                f.write(image_response.content)
            print("Image saved as test_image.jpg")
        else:
            print(f"Failed to fetch image: {image_response.status_code}")
            print(image_response.text)
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    test_cdn()