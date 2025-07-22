from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User


# Login Form for all users
class LoginForm(forms.Form):
    """Tailwind-styled login form for all user types"""

    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter your email',
            'required': True
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter your password',
            'required': True
        })
    )

# Customer Signup Form
class CustomerSignupForm(UserCreationForm):
    """Simple signup form for customers"""
    email = forms.EmailField(required=True)
    name = forms.CharField(max_length=100, required=True)
    username = forms.CharField(max_length=30, required=True)
    
    class Meta:
        model = User
        fields = ('email', 'username', 'name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        passed_email = kwargs.pop('email', None)
        super().__init__(*args, **kwargs)

        # Add Tailwind classes to each field
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'mt-1 block w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500',
            })

        # Read-only email (disable editing)
        if passed_email:
            self.fields['email'].initial  = passed_email
            self.fields['email'].widget.attrs.update({
                'readonly': 'readonly',
                'class': 'bg-gray-100 cursor-not-allowed mt-1 block w-full p-2 border border-gray-300 rounded-md',
                'placeholder': passed_email
            })

            self.fields['username'].widget.attrs.update({'placeholder': 'Your username'})
            self.fields['password1'].widget.attrs.update({'placeholder': 'Your password'})
            self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm your password'})
            self.fields['name'].widget.attrs.update({'placeholder': 'Your full name'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Email already exists.')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Username already exists.')
        return username
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords donot match!')
        return cleaned_data
    


# Agent Signup Form
class AgentSignupForm(UserCreationForm):
    """Signup form for agents - requires more details"""
    email = forms.EmailField(required=True)
    name = forms.CharField(max_length=100, required=True)
    username = forms.CharField(max_length=30, required=True)
    department = forms.CharField(max_length=50, required=True)
    
    class Meta:
        model = User
        fields = ('email', 'username', 'name', 'department', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        passed_email = kwargs.pop('email', None)
        super().__init__(*args, **kwargs)

        # Add Tailwind classes to each field
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'mt-1 block w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500',
            })

        # Read-only email (disable editing)
        if passed_email:
            self.fields['email'].initial  = passed_email
            self.fields['email'].widget.attrs.update({
                'readonly': 'readonly',
                'class': 'bg-gray-100 cursor-not-allowed mt-1 block w-full p-2 border border-gray-300 rounded-md',
                'placeholder': passed_email
            })

            self.fields['username'].widget.attrs.update({'placeholder': 'Choose a username'})
            self.fields['name'].widget.attrs.update({'placeholder': 'Your full name'})
            self.fields['department'].widget.attrs.update({'placeholder': 'Select your department'})
            self.fields['password1'].widget.attrs.update({'placeholder': 'Your password'})
            self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm your password'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Email already exists.')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords donot match!')
        return cleaned_data
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Username already exists.')
        return username