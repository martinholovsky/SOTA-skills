from rest_framework.views import APIView
from accounts.throttles import LoginRateThrottle

class LoginView(APIView):
    authentication_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        return login(request)
