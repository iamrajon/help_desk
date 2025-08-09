from rest_framework import serializers
from accounts.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class CustomerSignupSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True, min_length=5)
    password2 = serializers.CharField(write_only=True, min_length=5)

    class Meta:
        model = User
        fields = (
            'email',
            'username',
            'name',
            'phone',
            'password1',
            'password2'
        )

    def validate_email(self, value):
        """Check email format and uniqueness"""
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Enter a valid email address.")
        
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate(self, attrs):
        """
        validate password ie password1 should match password2
        """
        password1 = attrs.get('password1')
        password2 = attrs.get('password2')

        if password1 and password2 and password1 != password2:
            pass_error = {
                "password2": "Thew two passwords fields donot match!"
            }
            raise serializers.ValidationError(pass_error)
        return attrs
    
    def create(self, validated_data):
        """create customer User"""
        validated_data.pop('password2')
        password = validated_data.pop('password1')

        validated_data['user_type'] = User.UserType.CUSTOMER
        validated_data['is_verified'] = True

        user = User.objects.create_user(password=password, **validated_data)
        return user
    

