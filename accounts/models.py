from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with email and password"""
        if not email:
            raise ValueError('Email is required')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('user_type', User.UserType.SUPERUSER)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
            
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class UserType(models.TextChoices):
        CUSTOMER = 'customer', _('Customer')
        AGENT = 'agent', _('Agent/Supervisor')
        SUPERUSER = 'superuser', _('Superuser')

    # Core fields
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    user_type = models.CharField(
        max_length=10, 
        choices=UserType.choices, 
        default=UserType.CUSTOMER
    )
    
    # Contact information with validation
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be in format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(
        max_length=17, 
        validators=[phone_validator], 
        blank=True,
        help_text="Format: '+999999999'. Up to 15 digits allowed."
    )
    department = models.CharField(max_length=50, blank=True)
    
    # Status fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # 2fa for agent
    is_verified = models.BooleanField(default=True)  # Default True for customers
    verification_token = models.CharField(max_length=64, blank=True)
    verification_token_expiry = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name']
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.name}"
    
    def get_full_name(self):
        """Return the user's full name"""
        return self.name
    
    def profile_pic_url(self):
        if self.profile_pic:
            return self.profile_pic.url
        return f""
    
    @property
    def is_customer(self):
        """Check if user is a customer"""
        return self.user_type == self.UserType.CUSTOMER
    
    @property
    def is_agent(self):
        """Check if user is an agent/supervisor"""
        return self.user_type == self.UserType.AGENT
    
    @property
    def is_superuser_type(self):
        """Check if user is a superuser type (different from Django's is_superuser)"""
        return self.user_type == self.UserType.SUPERUSER
    
    def save(self, *args, **kwargs):
        """Override save to set staff status based on user type"""
        if self.user_type == self.UserType.SUPERUSER:
            self.is_superuser = True
            self.is_staff = True
        elif self.user_type == self.UserType.AGENT:
            self.is_staff = True

            # Agents need email verification by default
            if self._state.adding and self.user_type == self.UserType.AGENT:
                self.is_verified = False
        else:
            self.is_staff = False
            self.is_superuser = False
            # Customers don't need email verification
            if self.user_type == self.UserType.CUSTOMER:
                self.is_verified = True
        super().save(*args, **kwargs)