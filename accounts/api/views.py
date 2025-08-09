from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from accounts.api.serializers import CustomerSignupSerializer

from config.logger import get_logger
logger = get_logger(__name__)


class CustomerSignupView(APIView):
    def post(self, request):
        try:
            logger.debug(f"request data: {request.data}")
            serializer = CustomerSignupSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                logger.info(f"Customer {user} registered successfully")
                return Response({
                    "success": True,
                    "message": "Customer Registered Successfully"
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "success": False,
                    "message": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)