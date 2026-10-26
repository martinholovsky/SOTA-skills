from rest_framework.views import APIView

class LoginView(APIView):
    authentication_classes = []
    throttle_classes = []

    def post(self, request):
        return login(request)
