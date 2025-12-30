from fastapi import Request, Response
import uuid

async def get_user_id(request: Request, response: Response) -> str:
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())
        # Set cookie with long expiration (e.g., 1 year)
        # HTTPOnly is recommended for security (not accessible by JS)
        # SameSite='Lax' allows it to be sent with top-level navigations
        response.set_cookie(
            key="user_id", 
            value=user_id, 
            httponly=True, 
            max_age=31536000, 
            samesite="none",
            secure=True,
        )
    return user_id
