from django.http import HttpResponse, JsonResponse  # type: ignore
from django.shortcuts import render, redirect  # type: ignore
from django.contrib.auth.models import User  # type: ignore
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout  # type: ignore
from django.contrib.auth.decorators import login_required  # type: ignore
from django.core.mail import send_mail  # type: ignore
from django.core.files.storage import default_storage  # type: ignore
from django.core.files.base import ContentFile  # type: ignore
from tensorflow.keras.preprocessing import image  # type: ignore
import cv2  # type: ignore
import numpy as np  # type: ignore
import os  # type: ignore
from django.conf import settings  # type: ignore

# from .forms import ImageUploadForm  # type: ignore
from tensorflow.keras.models import load_model  # type: ignore


from django.core.mail import send_mail
from django.conf import settings


# Load model
try:
    MODEL_PATH = os.path.join(settings.BASE_DIR, 'models/model.h5')
    model = load_model(MODEL_PATH)
except Exception as e:
    model = None
    print(f"Error loading model: {e}")


from django.core.mail import send_mail
from django.conf import settings

def send_mail_page(request):
    context = {}

    if request.method == 'POST':
        address = request.POST.get('address')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        if address and subject and message:
            try:
                send_mail(subject, message, settings.EMAIL_HOST_USER, [address])
                context['result'] = 'Email sent successfully'
            except Exception as e:
                context['result'] = f'Error sending email: {e}'
        else:
            context['result'] = 'All fields are required'
    
    return render(request, "sendmail.html", context)


def index(request):
    return render(request, "index.html")

@login_required(login_url='login')
def home(request):
    uploaded_image_url = request.session.get('uploaded_image_url')
    return render(request, 'home.html', {'uploaded_image_url': uploaded_image_url})

def send_welcome_mail(user_email):
    subject = 'Welcome to my Traffic Sign Prediction Application'
    message = (
        'Thank you for showing interest in our website. '
        'We are excited to have you.'
    )
    from_email = settings.EMAIL_HOST_USER
    receivers_email = [user_email]

    try:
        send_mail(subject, message, from_email, receivers_email)
    except Exception as e:
        # Log the error and inform the user
        print(f"Email sending failed: {e}")
        return False
    return True
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth.models import User
def signup(request):
    if request.method == 'POST':
        uname = request.POST.get('username')
        email = request.POST.get('email')
        pass1 = request.POST.get('password1')
        pass2 = request.POST.get('password2')
        
        # Check if username already exists
        if User.objects.filter(username=uname).exists():
            return HttpResponse('error' 'Username already exists!')

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            return HttpResponse('error' 'Email already exists!')

        # Validate password
        try:
            validate_password(pass1)
        except ValidationError as e:
            return render(request, 'signup.html', {'error': e})

        # Create user and send welcome email
        user = User.objects.create_user(uname, email, pass1)
        email_sent = send_welcome_mail(email)
        if not email_sent:
            messages.error(request, 'Registration successful, but failed to send welcome email.')

        messages.success(request, 'Registration successful!')
        return redirect('login')

    return render(request, "signup.html")

def login_view(request):
    if request.method == "POST":
        email= request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, email=email, password=password)
        if user:
            auth_login(request, user)
            return redirect('home')
        else:
            return HttpResponse({'error: Invalid credentials.'})
    return render(request, 'login.html')

def logout_view(request):
    auth_logout(request)
    return redirect('login')


from django.contrib.auth.forms import PasswordResetForm
def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        form = PasswordResetForm({'email': email})
        
        if form.is_valid():
            form.save(
                request=request,
                use_https=False,
                email_template_name='registration/password_reset_email.html',
            )
            return HttpResponse("A password reset link has been sent to your email.")
        else:
            return render(request, 'forgot_password.html', {'error': 'Invalid email address'})
    
    return render(request, 'forgot_password.html')





# Helper functions for image preprocessing
def grayscale(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

def equalize(img):
    return cv2.equalizeHist(img)

def preprocessing(img):
    img = grayscale(img)
    img = equalize(img)
    return img / 255.0

def getClassName(classNo):
    classes = [
        'Speed Limit 20 km/h', 'Speed Limit 30 km/h', 'Speed Limit 50 km/h', 'Speed Limit 60 km/h',
        'Speed Limit 70 km/h', 'Speed Limit 80 km/h', 'End of Speed Limit 80 km/h', 'Speed Limit 100 km/h',
        'Speed Limit 120 km/h', 'No passing', 'No passing for vehicles over 3.5 metric tons',
        'Right-of-way at the next intersection', 'Priority road', 'Yield', 'Stop', 'No vehicles',
        'Vehicles over 3.5 metric tons prohibited', 'No entry', 'General caution', 'Dangerous curve to the left',
        'Dangerous curve to the right', 'Double curve', 'Bumpy road', 'Slippery road', 'Road narrows on the right',
        'Road work', 'Traffic signals', 'Pedestrians', 'Children crossing', 'Bicycles crossing', 'Beware of ice/snow',
        'Wild animals crossing', 'End of all speed and passing limits', 'Turn right ahead', 'Turn left ahead',
        'Ahead only', 'Go straight or right', 'Go straight or left', 'Keep right', 'Keep left', 'Roundabout mandatory',
        'End of no passing', 'End of no passing by vehicles over 3.5 metric tons'
    ]
    return classes[classNo] if classNo < len(classes) else "Unknown"

def model_predict(img_path, model):
    if model is None:
        return "Model not loaded"
    img = image.load_img(img_path, target_size=(32, 32))
    img = np.array(img)
    img = preprocessing(img)
    img = img.reshape(1, 32, 32, 1)
    predictions = model.predict(img)
    classIndex = np.argmax(predictions, axis=-1)[0]
    return getClassName(classIndex)

def upload_and_predict(request):
    if request.method == 'POST' and 'file' in request.FILES:
        f = request.FILES['file']
        file_path = default_storage.save(f'uploads/{f.name}', ContentFile(f.read()))
        full_file_path = os.path.join(settings.MEDIA_ROOT, file_path)
        result = model_predict(full_file_path, model)
        return JsonResponse({'result': result})
    return JsonResponse({'error': 'Invalid request'}, status=400)
